import logging
from datetime import timedelta

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import get_user_model
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .serializers import (
    CustomTokenObtainPairSerializer, VerifyOTPSerializer, ResendOTPSerializer, CreatePasswordSerializer,
    RegisterSerializer, UserSerializer, AddressSerializer,
    ChangePasswordSerializer, ForgotPasswordSerializer, ResetPasswordSerializer,
)
from .models import Address, PasswordResetToken, EmailOTP
from .email_utils import (
    dispatch_otp_email,
    dispatch_welcome_email,
    dispatch_login_notification,
    dispatch_password_reset_email,
)
import random
import string

User = get_user_model()
logger = logging.getLogger(__name__)


def _parse_device(ua: str) -> str:
    """
    Extract a human-readable 'Browser on OS' string from a raw User-Agent.
    Uses only the stdlib — no extra packages required.
    """
    ua = ua or ''
    # --- Browser ---
    if 'Edg/' in ua or 'Edge/' in ua:
        browser = 'Microsoft Edge'
    elif 'OPR/' in ua or 'Opera/' in ua:
        browser = 'Opera'
    elif 'Chrome/' in ua and 'Chromium/' not in ua:
        browser = 'Chrome'
    elif 'Firefox/' in ua:
        browser = 'Firefox'
    elif 'Safari/' in ua and 'Chrome/' not in ua:
        browser = 'Safari'
    elif 'MSIE' in ua or 'Trident/' in ua:
        browser = 'Internet Explorer'
    else:
        browser = 'Unknown Browser'

    # --- OS ---
    if 'Windows NT 10.0' in ua:
        os_ = 'Windows 10/11'
    elif 'Windows NT 6.3' in ua:
        os_ = 'Windows 8.1'
    elif 'Windows NT 6.1' in ua:
        os_ = 'Windows 7'
    elif 'Windows' in ua:
        os_ = 'Windows'
    elif 'Mac OS X' in ua:
        os_ = 'macOS'
    elif 'Android' in ua:
        os_ = 'Android'
    elif 'iPhone' in ua or 'iPad' in ua:
        os_ = 'iOS'
    elif 'Linux' in ua:
        os_ = 'Linux'
    else:
        os_ = 'Unknown OS'

    return f'{browser} on {os_}'


class LoginRateThrottle(AnonRateThrottle):
    rate = '10/minute'
    scope = 'login'


class ThrottledTokenObtainPairView(TokenObtainPairView):
    """Rate-limited email+password login — 10 attempts per minute per IP."""
    throttle_classes = [LoginRateThrottle]
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            user_email = request.data.get('email', '')
            ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', 'unknown'))
            if ',' in ip:
                ip = ip.split(',')[0].strip()
            ua = request.META.get('HTTP_USER_AGENT', 'unknown')

            # Format timestamp in IST (Django TIME_ZONE = 'Asia/Kolkata')
            from django.utils import timezone as tz
            import zoneinfo
            ist = zoneinfo.ZoneInfo('Asia/Kolkata')
            now_ist = tz.now().astimezone(ist)
            ts = now_ist.strftime('%d %b %Y, %I:%M %p IST')

            # Parse browser/OS from User-Agent
            device = _parse_device(ua)

            dispatch_login_notification(user_email, ip, ua, ts, device)
        return response


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        email = data['email'].lower().strip()

        # ── CASE 1: Fully verified + active user → block ──────────────────────
        existing = User.objects.filter(email=email).first()
        if existing and existing.is_email_verified:
            return Response(
                {'email': 'An account with this email already exists. Please log in.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── CASE 2: Unverified user exists → reuse, resend OTP ───────────────
        if existing and not existing.is_email_verified:
            user = existing
            # Update profile fields in case user wants to correct them
            user.first_name = data['first_name']
            user.last_name = data['last_name']
            user.phone = data.get('phone', user.phone)
            user.role = data.get('role', user.role)
            user.save(update_fields=['first_name', 'last_name', 'phone', 'role'])
            logger.info(f"[register] Unverified user {email} re-registering — reusing account.")

        # ── CASE 3: Brand-new user → create ──────────────────────────────────
        else:
            username = email.split('@')[0]
            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1

            user = User(
                username=username,
                email=email,
                first_name=data['first_name'],
                last_name=data['last_name'],
                phone=data.get('phone', ''),
                role=data.get('role', 'buyer'),
                is_email_verified=False,
                is_active=False,
            )
            user.set_unusable_password()
            user.save()
            logger.info(f"[register] New user created: {email}")

        # ── Generate fresh OTP (invalidate all previous ones) ─────────────────
        EmailOTP.objects.filter(user=user, is_used=False).update(is_used=True)
        otp_code = ''.join(random.choices(string.digits, k=6))
        EmailOTP.objects.create(user=user, code=otp_code)
        logger.info(f"[otp] OTP generated for {email}")

        # Non-blocking dispatch (Celery or thread fallback)
        dispatch_otp_email(user.email, otp_code)

        return Response(
            {
                'message': 'OTP sent to your email. Please verify to continue.',
                'email': email,
                'resent': existing is not None,
            },
            status=status.HTTP_200_OK,
        )



class LogoutView(APIView):
    """POST /api/users/logout/ — Blacklist the refresh token."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({'error': 'Refresh token is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'message': 'Logged out successfully.'}, status=status.HTTP_200_OK)


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        if not request.user.check_password(serializer.validated_data['old_password']):
            return Response({"error": "Old password is incorrect."}, status=status.HTTP_400_BAD_REQUEST)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()
        return Response({"message": "Password changed successfully."})


class ForgotPasswordView(APIView):
    """POST /api/users/forgot-password/ — Send reset link to email."""
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email']
        try:
            user = User.objects.get(email=email)
            # Invalidate all existing unused tokens
            PasswordResetToken.objects.filter(user=user, is_used=False).delete()
            token_obj = PasswordResetToken(user=user)
            token_obj.expires_at = timezone.now() + timedelta(hours=1)
            token_obj.save()

            reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token_obj.token}"
            dispatch_password_reset_email(email, user.first_name or user.username, reset_url)
            logger.info(f"Password reset email dispatched for {email}")
        except User.DoesNotExist:
            pass  # Never reveal whether the email exists

        return Response({
            'message': 'If this email is registered, a reset link has been sent.'
        })


class ResetPasswordView(APIView):
    """POST /api/users/reset-password/ — Consume token, set new password."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        token_value = serializer.validated_data['token']
        try:
            reset_token = PasswordResetToken.objects.select_related('user').get(token=token_value)
        except PasswordResetToken.DoesNotExist:
            return Response({'error': 'Invalid or expired token.'}, status=status.HTTP_400_BAD_REQUEST)

        if not reset_token.is_valid:
            return Response({'error': 'Token has expired or already been used.'}, status=status.HTTP_400_BAD_REQUEST)

        user = reset_token.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        reset_token.is_used = True
        reset_token.save(update_fields=['is_used'])

        return Response({'message': 'Password reset successfully. Please log in with your new password.'})


class AddressListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        addresses = request.user.addresses.all()
        return Response(AddressSerializer(addresses, many=True).data)

    def post(self, request):
        serializer = AddressSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AddressDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request, pk):
        return get_object_or_404(Address, pk=pk, user=request.user)

    def get(self, request, pk):
        return Response(AddressSerializer(self.get_object(request, pk)).data)

    def patch(self, request, pk):
        address = self.get_object(request, pk)
        serializer = AddressSerializer(address, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        self.get_object(request, pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class VerifyOTPView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        email = serializer.validated_data['email']
        code = serializer.validated_data['code']
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'error': 'Invalid request.'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            otp = EmailOTP.objects.filter(user=user, is_used=False).latest('created_at')
        except EmailOTP.DoesNotExist:
            return Response({'error': 'No active OTP found.'}, status=status.HTTP_400_BAD_REQUEST)
            
        if not otp.is_valid:
            return Response({'error': 'OTP expired or maximum attempts reached.'}, status=status.HTTP_400_BAD_REQUEST)
            
        if otp.code != code:
            otp.attempts += 1
            otp.save(update_fields=['attempts'])
            return Response({'error': 'Invalid OTP code.'}, status=status.HTTP_400_BAD_REQUEST)
            
        # Success
        otp.is_used = True
        otp.save(update_fields=['is_used'])
        user.is_email_verified = True
        user.save(update_fields=['is_email_verified'])
        
        # Generate token for password creation
        PasswordResetToken.objects.filter(user=user, is_used=False).delete()
        token_obj = PasswordResetToken(user=user)
        token_obj.expires_at = timezone.now() + timedelta(hours=1)
        token_obj.save()
        
        # Send welcome email — non-blocking
        dispatch_welcome_email(user.email, user.first_name or user.username)
        
        return Response({
            'message': 'Email verified successfully. Please create a password.',
            'token': token_obj.token
        })

class ResendOTPView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        serializer = ResendOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        email = serializer.validated_data['email']
        try:
            user = User.objects.get(email=email)
            if user.is_email_verified:
                return Response({'error': 'Email already verified.'}, status=status.HTTP_400_BAD_REQUEST)
                
            # Check cooldown (1 minute)
            last_otp = EmailOTP.objects.filter(user=user).order_by('-created_at').first()
            if last_otp and (timezone.now() - last_otp.created_at).total_seconds() < 60:
                return Response({'error': 'Please wait before requesting a new OTP.'}, status=status.HTTP_400_BAD_REQUEST)
                
            # Generate new OTP
            otp_code = ''.join(random.choices(string.digits, k=6))
            EmailOTP.objects.create(user=user, code=otp_code)
            # Non-blocking dispatch
            dispatch_otp_email(user.email, otp_code)
            return Response({'message': 'New OTP sent successfully.'})
            
        except User.DoesNotExist:
            pass # Silent failure
            
        return Response({'message': 'If the email exists, a new OTP has been sent.'})

class CreatePasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = CreatePasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        token_value = serializer.validated_data['token']
        try:
            reset_token = PasswordResetToken.objects.select_related('user').get(token=token_value)
        except PasswordResetToken.DoesNotExist:
            return Response({'error': 'Invalid or expired token.'}, status=status.HTTP_400_BAD_REQUEST)

        if not reset_token.is_valid:
            return Response({'error': 'Token has expired or already been used.'}, status=status.HTTP_400_BAD_REQUEST)

        user = reset_token.user
        user.set_password(serializer.validated_data['password'])
        user.is_active = True
        user.save()
        
        reset_token.is_used = True
        reset_token.save(update_fields=['is_used'])

        return Response({'message': 'Password created successfully. You can now log in.'})
