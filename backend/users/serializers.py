from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model
from .models import Address

User = get_user_model()


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = [
            'id', 'full_name', 'phone', 'address_line1', 'address_line2',
            'city', 'state', 'pincode', 'country', 'address_type', 'is_default',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'phone', 'role', 'profile_picture', 'created_at']
        read_only_fields = ['id', 'role', 'created_at']


class UserPublicSerializer(serializers.ModelSerializer):
    """Minimal public profile — safe to expose in reviews/orders."""
    class Meta:
        model = User
        fields = ['id', 'username', 'profile_picture']


class RegisterSerializer(serializers.Serializer):
    """
    Plain Serializer (not ModelSerializer) so DRF never fires the built-in
    unique-email validator. The view handles verified vs unverified logic.
    """
    first_name = serializers.CharField(required=True, max_length=150)
    last_name = serializers.CharField(required=True, max_length=150)
    email = serializers.EmailField(required=True)
    phone = serializers.CharField(required=False, allow_blank=True, max_length=20, default='')
    role = serializers.ChoiceField(choices=['buyer', 'seller'], default='buyer')

class CreatePasswordSerializer(serializers.Serializer):
    token = serializers.UUIDField()
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password_confirm': 'Passwords do not match.'})
        return attrs



class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    new_password2 = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError({'new_password2': 'New passwords do not match.'})
        return attrs


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    token = serializers.UUIDField()
    new_password = serializers.CharField(write_only=True, min_length=8)
    new_password2 = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError({'new_password2': 'Passwords do not match.'})
        return attrs

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Override SimpleJWT's login serializer to accept email + password.

    SimpleJWT determines the login field from USERNAME_FIELD (which is
    'username' on our model). We override username_field to 'email' locally
    so the serializer exposes an `email` field, then authenticate via our
    custom EmailAuthBackend.
    """

    username_field = 'email'

    email = serializers.EmailField(required=True, write_only=True)
    password = serializers.CharField(
        required=True, write_only=True, style={'input_type': 'password'}
    )

    def validate(self, attrs):
        from django.contrib.auth import authenticate

        email = attrs.get('email', '').lower().strip()
        password = attrs.get('password', '')

        user = authenticate(request=self.context.get('request'), email=email, password=password)

        if user is None:
            raise serializers.ValidationError(
                {'detail': 'Invalid email or password. Please try again.'}
            )

        if not user.is_active:
            raise serializers.ValidationError(
                {'detail': 'This account has been deactivated. Contact support.'}
            )

        if not user.is_email_verified:
            raise serializers.ValidationError(
                {'detail': 'Email not verified. Please complete OTP verification.', 'needs_verification': True}
            )

        # Generate JWT tokens
        refresh = self.get_token(user)
        data = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': {
                'id': user.id,
                'email': user.email,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role,
                'is_email_verified': user.is_email_verified,
            },
        }
        return data


class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6)

class ResendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
