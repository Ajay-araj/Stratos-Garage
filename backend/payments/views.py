import hashlib
import hmac
import json
import logging

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Payment, Refund, SellerPayout
from .serializers import (
    PaymentSerializer, PaymentInitiateSerializer,
    PaymentVerifySerializer, SellerPayoutSerializer, RefundSerializer,
)
from orders.models import Order, OrderItem, Notification
from sellers.models import Seller
from Stratosgarage.permissions import IsVerifiedSeller, IsAdminUser

logger = logging.getLogger(__name__)


def _get_razorpay_client():
    import razorpay
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def _create_payouts(payment, order):
    """Create SellerPayout records for each order item (idempotent)."""
    for item in order.items.select_related('variant__product__seller', 'seller'):
        seller = item.seller or (item.variant.product.seller if item.variant else None)
        if not seller:
            continue
        gross = item.subtotal
        commission = round(gross * seller.commission_rate / 100, 2)
        net = round(gross - commission, 2)
        SellerPayout.objects.get_or_create(
            payment=payment,
            order_item=item,
            defaults={
                'seller': seller,
                'gross_amount': gross,
                'platform_commission': commission,
                'seller_amount': net,
                'payout_status': 'pending',
            },
        )


class PaymentInitiateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PaymentInitiateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        order = get_object_or_404(Order, pk=serializer.validated_data['order_id'], user=request.user)

        if order.payment_status == 'completed':
            return Response({'error': 'Order is already paid.'}, status=status.HTTP_400_BAD_REQUEST)

        gateway = serializer.validated_data['payment_gateway']

        # Reuse existing payment record if one exists
        if hasattr(order, 'payment'):
            payment = order.payment
        else:
            payment = None

        # ── Cash on Delivery ──────────────────────────────────────────────────
        if gateway == 'cod':
            with transaction.atomic():
                if payment is None:
                    import uuid
                    payment = Payment.objects.create(
                        order=order,
                        user=request.user,
                        payment_gateway='cod',
                        gateway_order_id=f"COD_{uuid.uuid4().hex[:12].upper()}",
                        amount=order.total_price,
                        currency='INR',
                        status='pending',
                    )
                else:
                    payment.status = 'pending'
                    payment.save(update_fields=['status'])

                order.payment_status = 'pending'
                order.order_status = 'confirmed'
                order.save(update_fields=['payment_status', 'order_status', 'updated_at'])
                _create_payouts(payment, order)

            Notification.objects.create(
                user=request.user,
                notification_type='order_confirmed',
                title=f"Order #{order.order_number} Confirmed (COD)",
                message=f"Your cash-on-delivery order of ₹{order.total_price} is confirmed.",
                related_order=order,
            )
            return Response({
                'message': 'COD order confirmed.',
                'payment_id': payment.id,
                'gateway_order_id': payment.gateway_order_id,
                'amount': str(payment.amount),
                'currency': payment.currency,
                'payment_gateway': 'cod',
                'order_number': order.order_number,
            })

        # ── Razorpay ──────────────────────────────────────────────────────────
        if gateway == 'razorpay':
            if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
                logger.error("Razorpay credentials not configured.")
                return Response(
                    {'error': 'Payment gateway not configured. Contact support.'},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

            # If payment already exists and has a valid gateway_order_id, reuse it
            if payment and payment.gateway_order_id and payment.gateway_order_id.startswith('order_'):
                return Response({
                    'payment_id': payment.id,
                    'gateway_order_id': payment.gateway_order_id,
                    'amount': str(payment.amount),
                    'currency': payment.currency,
                    'payment_gateway': 'razorpay',
                    'razorpay_key_id': settings.RAZORPAY_KEY_ID,
                    'order_number': order.order_number,
                })

            try:
                client = _get_razorpay_client()
                # Razorpay expects amount in paise (integer)
                amount_paise = int(order.total_price * 100)
                rz_order = client.order.create({
                    'amount': amount_paise,
                    'currency': 'INR',
                    'receipt': order.order_number,
                    'notes': {
                        'order_number': order.order_number,
                        'user_id': str(request.user.id),
                    },
                })
                gateway_order_id = rz_order['id']
            except Exception as exc:
                logger.exception(f"Razorpay order creation failed for order {order.order_number}: {exc}")
                return Response(
                    {'error': 'Payment gateway error. Please try again.'},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

            with transaction.atomic():
                if payment is None:
                    payment = Payment.objects.create(
                        order=order,
                        user=request.user,
                        payment_gateway='razorpay',
                        gateway_order_id=gateway_order_id,
                        amount=order.total_price,
                        currency='INR',
                        status='initiated',
                    )
                else:
                    payment.payment_gateway = 'razorpay'
                    payment.gateway_order_id = gateway_order_id
                    payment.amount = order.total_price
                    payment.status = 'initiated'
                    payment.save(update_fields=['payment_gateway', 'gateway_order_id', 'amount', 'status'])

            logger.info(f"Razorpay order created: {gateway_order_id} for order {order.order_number}")
            return Response({
                'payment_id': payment.id,
                'gateway_order_id': gateway_order_id,
                'amount': str(payment.amount),
                'amount_paise': int(payment.amount * 100),
                'currency': payment.currency,
                'payment_gateway': 'razorpay',
                'razorpay_key_id': settings.RAZORPAY_KEY_ID,
                'order_number': order.order_number,
            })

        return Response({'error': f"Unsupported gateway: {gateway}"}, status=status.HTTP_400_BAD_REQUEST)


class PaymentVerifyView(APIView):
    """POST /api/payments/verify/ — Client-side callback after Razorpay checkout."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PaymentVerifySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        payment = get_object_or_404(
            Payment,
            gateway_order_id=serializer.validated_data['gateway_order_id'],
            user=request.user,
        )

        if payment.status == 'completed':
            return Response({'message': 'Payment already verified.', 'payment': PaymentSerializer(payment).data})

        # ── Razorpay HMAC signature verification ──────────────────────────────
        if payment.payment_gateway == 'razorpay':
            key_secret = settings.RAZORPAY_KEY_SECRET
            gateway_payment_id = serializer.validated_data.get('gateway_payment_id', '')
            gateway_signature = serializer.validated_data.get('gateway_signature', '')

            if not key_secret:
                logger.error("RAZORPAY_KEY_SECRET not set — cannot verify signature.")
                return Response({'error': 'Gateway misconfiguration.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

            if not gateway_payment_id or not gateway_signature:
                return Response({'error': 'gateway_payment_id and gateway_signature are required for Razorpay.'}, status=status.HTTP_400_BAD_REQUEST)

            msg = f"{payment.gateway_order_id}|{gateway_payment_id}"
            generated = hmac.new(
                key_secret.encode('utf-8'),
                msg.encode('utf-8'),
                hashlib.sha256,
            ).hexdigest()

            if not hmac.compare_digest(generated, gateway_signature):
                payment.status = 'failed'
                payment.failure_reason = 'Signature verification failed.'
                payment.save(update_fields=['status', 'failure_reason'])
                logger.warning(f"Razorpay signature mismatch for payment {payment.id}")
                return Response({'error': 'Signature verification failed.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            payment.gateway_payment_id = serializer.validated_data.get('gateway_payment_id', '')
            payment.gateway_signature = serializer.validated_data.get('gateway_signature', '')
            payment.status = 'completed'
            payment.completed_at = timezone.now()
            payment.save()

            order = payment.order
            order.payment_status = 'completed'
            order.order_status = 'confirmed'
            order.save(update_fields=['payment_status', 'order_status', 'updated_at'])
            _create_payouts(payment, order)

        Notification.objects.create(
            user=request.user,
            notification_type='payment_success',
            title=f"Payment Confirmed — Order #{order.order_number}",
            message=f"₹{payment.amount} payment received successfully.",
            related_order=order,
        )
        logger.info(f"Payment verified: {payment.id} for order {order.order_number}")
        return Response({'message': 'Payment verified.', 'payment': PaymentSerializer(payment).data})


@method_decorator(csrf_exempt, name='dispatch')
class RazorpayWebhookView(APIView):
    """POST /api/payments/webhook/razorpay/ — Server-side async event handler."""
    permission_classes = [AllowAny]

    def post(self, request):
        webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET if hasattr(settings, 'RAZORPAY_WEBHOOK_SECRET') else ''

        # Verify webhook signature if secret is configured
        if webhook_secret:
            signature = request.headers.get('X-Razorpay-Signature', '')
            body = request.body
            generated = hmac.new(
                webhook_secret.encode('utf-8'),
                body,
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(generated, signature):
                logger.warning("Razorpay webhook signature verification failed.")
                return Response({'error': 'Invalid signature.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            payload = json.loads(request.body)
        except (json.JSONDecodeError, Exception):
            return Response({'error': 'Invalid JSON payload.'}, status=status.HTTP_400_BAD_REQUEST)

        event = payload.get('event', '')
        logger.info(f"Razorpay webhook received: {event}")

        if event == 'payment.captured':
            payment_entity = payload.get('payload', {}).get('payment', {}).get('entity', {})
            rz_order_id = payment_entity.get('order_id', '')
            rz_payment_id = payment_entity.get('id', '')
            rz_signature = ''  # Not provided in webhook payload; trust server-side event

            try:
                payment = Payment.objects.select_related('order').get(gateway_order_id=rz_order_id)
            except Payment.DoesNotExist:
                logger.error(f"Webhook: payment not found for gateway_order_id={rz_order_id}")
                return Response({'status': 'ok'})  # ACK to Razorpay regardless

            if payment.status != 'completed':
                with transaction.atomic():
                    payment.gateway_payment_id = rz_payment_id
                    payment.status = 'completed'
                    payment.completed_at = timezone.now()
                    payment.save(update_fields=['gateway_payment_id', 'status', 'completed_at'])

                    order = payment.order
                    order.payment_status = 'completed'
                    order.order_status = 'confirmed'
                    order.save(update_fields=['payment_status', 'order_status', 'updated_at'])
                    _create_payouts(payment, order)
                logger.info(f"Webhook payment.captured processed: order={order.order_number}")

        elif event == 'payment.failed':
            payment_entity = payload.get('payload', {}).get('payment', {}).get('entity', {})
            rz_order_id = payment_entity.get('order_id', '')
            try:
                payment = Payment.objects.get(gateway_order_id=rz_order_id)
                if payment.status not in ('completed', 'failed'):
                    payment.status = 'failed'
                    payment.failure_reason = payment_entity.get('error_description', 'Payment failed.')
                    payment.save(update_fields=['status', 'failure_reason'])
            except Payment.DoesNotExist:
                pass

        elif event == 'refund.created':
            refund_entity = payload.get('payload', {}).get('refund', {}).get('entity', {})
            gateway_refund_id = refund_entity.get('id', '')
            rz_payment_id = refund_entity.get('payment_id', '')
            try:
                payment = Payment.objects.get(gateway_payment_id=rz_payment_id)
                Refund.objects.filter(payment=payment, gateway_refund_id='').update(
                    gateway_refund_id=gateway_refund_id,
                    status='processing',
                )
            except Payment.DoesNotExist:
                pass

        return Response({'status': 'ok'})


class PaymentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_number):
        order = get_object_or_404(Order, order_number=order_number, user=request.user)
        payment = get_object_or_404(Payment, order=order)
        return Response(PaymentSerializer(payment).data)


class SellerPayoutListView(APIView):
    permission_classes = [IsAuthenticated, IsVerifiedSeller]

    def get(self, request):
        seller = get_object_or_404(Seller, user=request.user)
        payouts = (
            SellerPayout.objects
            .filter(seller=seller)
            .select_related('order_item', 'payment')
            .order_by('-created_at')
        )
        return Response(SellerPayoutSerializer(payouts, many=True).data)


class RefundCreateView(APIView):
    """POST /api/payments/<order_number>/refund/ — Admin initiates refund via gateway."""
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request, order_number):
        order = get_object_or_404(Order, order_number=order_number)
        payment = get_object_or_404(Payment, order=order, status='completed')

        serializer = RefundSerializer(data=request.data, context={'payment': payment})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        amount = serializer.validated_data['amount']
        reason = serializer.validated_data.get('reason', '')

        gateway_refund_id = ''
        if payment.payment_gateway == 'razorpay' and payment.gateway_payment_id:
            if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
                return Response({'error': 'Razorpay credentials not configured.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            try:
                client = _get_razorpay_client()
                refund_response = client.payment.refund(
                    payment.gateway_payment_id,
                    {
                        'amount': int(amount * 100),  # paise
                        'notes': {'reason': reason, 'order_number': order_number},
                    }
                )
                gateway_refund_id = refund_response.get('id', '')
                logger.info(f"Razorpay refund created: {gateway_refund_id} for payment {payment.id}")
            except Exception as exc:
                logger.exception(f"Razorpay refund failed for payment {payment.id}: {exc}")
                return Response(
                    {'error': 'Refund gateway error. Please retry or process manually.'},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

        refund = serializer.save(
            payment=payment,
            gateway_refund_id=gateway_refund_id,
            status='processing' if gateway_refund_id else 'initiated',
        )
        return Response(RefundSerializer(refund).data, status=status.HTTP_201_CREATED)


class PayoutProcessView(APIView):
    """PATCH /api/payments/payouts/<pk>/process/ — Admin marks payout as completed."""
    permission_classes = [IsAuthenticated, IsAdminUser]

    def patch(self, request, pk):
        payout = get_object_or_404(SellerPayout, pk=pk)
        if payout.payout_status == 'completed':
            return Response({'error': 'Payout already completed.'}, status=status.HTTP_400_BAD_REQUEST)

        payout_reference = request.data.get('payout_reference', '').strip()
        if not payout_reference:
            return Response({'error': 'payout_reference is required.'}, status=status.HTTP_400_BAD_REQUEST)

        payout.payout_status = 'completed'
        payout.payout_reference = payout_reference
        payout.payout_date = timezone.now()
        payout.save(update_fields=['payout_status', 'payout_reference', 'payout_date'])

        return Response(SellerPayoutSerializer(payout).data)


class AdminPayoutListView(APIView):
    """GET /api/payments/payouts/ — Admin view all payouts."""
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        payout_status = request.query_params.get('status', '')
        qs = SellerPayout.objects.select_related('seller', 'order_item', 'payment').order_by('-created_at')
        if payout_status:
            qs = qs.filter(payout_status=payout_status)
        return Response(SellerPayoutSerializer(qs, many=True).data)
