"""
Payment flow tests: Razorpay initiation, verification, webhook,
refund creation, and payout processing.
"""
import pytest
import hmac
import hashlib
import json
from decimal import Decimal
from unittest.mock import patch, MagicMock
from rest_framework import status
from django.conf import settings


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_razorpay_signature(order_id: str, payment_id: str, secret: str) -> str:
    """Replicate the HMAC-SHA256 Razorpay signature for verify tests."""
    payload = f"{order_id}|{payment_id}"
    return hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()


def _make_webhook_signature(body: bytes, secret: str) -> str:
    return hmac.new(
        secret.encode('utf-8'),
        body,
        hashlib.sha256,
    ).hexdigest()


# ─── Payment Initiate ─────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestPaymentInitiate:
    url = '/api/payments/initiate/'

    @patch('payments.views._get_razorpay_client')
    def test_initiate_razorpay_success(self, mock_client_fn, buyer_client, placed_order):
        mock_client = MagicMock()
        mock_client.order.create.return_value = {
            'id': 'order_FAKE123',
            'amount': int(placed_order.total_price * 100),
            'currency': 'INR',
        }
        mock_client_fn.return_value = mock_client
        resp = buyer_client.post(self.url, {
            'order_id': placed_order.id,
            'payment_gateway': 'razorpay',
        })
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['payment_gateway'] == 'razorpay'
        assert 'gateway_order_id' in resp.data
        assert resp.data['amount'] == str(placed_order.total_price)

    @patch('payments.views._get_razorpay_client')
    def test_initiate_razorpay_creates_payment_record(self, mock_client_fn, buyer_client, placed_order):
        from payments.models import Payment
        mock_client = MagicMock()
        mock_client.order.create.return_value = {
            'id': 'order_DB_TEST',
            'amount': int(placed_order.total_price * 100),
            'currency': 'INR',
        }
        mock_client_fn.return_value = mock_client
        buyer_client.post(self.url, {
            'order_id': placed_order.id,
            'payment_gateway': 'razorpay',
        })
        assert Payment.objects.filter(
            order=placed_order, payment_gateway='razorpay',
        ).exists()

    def test_initiate_cod_success(self, buyer_client, placed_order):
        resp = buyer_client.post(self.url, {
            'order_id': placed_order.id,
            'payment_gateway': 'cod',
        })
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['payment_gateway'] == 'cod'

    def test_initiate_phonepe_rejected(self, buyer_client, placed_order):
        """phonepe is not in the valid choices — must be rejected at serializer."""
        resp = buyer_client.post(self.url, {
            'order_id': placed_order.id,
            'payment_gateway': 'phonepe',
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_initiate_nonexistent_order(self, buyer_client):
        resp = buyer_client.post(self.url, {
            'order_id': 99999,
            'payment_gateway': 'razorpay',
        })
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_initiate_other_users_order_blocked(self, buyer2_client, placed_order):
        resp = buyer2_client.post(self.url, {
            'order_id': placed_order.id,
            'payment_gateway': 'razorpay',
        })
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_initiate_already_completed_order_blocked(self, buyer_client, placed_order):
        placed_order.payment_status = 'completed'
        placed_order.save()
        resp = buyer_client.post(self.url, {
            'order_id': placed_order.id,
            'payment_gateway': 'razorpay',
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_initiate_requires_auth(self, api_client, placed_order):
        resp = api_client.post(self.url, {
            'order_id': placed_order.id,
            'payment_gateway': 'razorpay',
        })
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_initiate_missing_gateway(self, buyer_client, placed_order):
        resp = buyer_client.post(self.url, {'order_id': placed_order.id})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_initiate_missing_order_id(self, buyer_client):
        resp = buyer_client.post(self.url, {'payment_gateway': 'razorpay'})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# ─── Payment Verify ───────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestPaymentVerify:
    url = '/api/payments/verify/'

    def _create_payment(self, placed_order, buyer):
        from payments.models import Payment
        return Payment.objects.create(
            order=placed_order,
            user=buyer,
            payment_gateway='razorpay',
            gateway_order_id='order_VERIFY_TEST',
            amount=placed_order.total_price,
            currency='INR',
            status='pending',
        )

    def test_verify_valid_signature(self, buyer_client, placed_order, buyer):
        payment = self._create_payment(placed_order, buyer)
        payment_id = 'pay_FAKE999'
        secret = getattr(settings, 'RAZORPAY_KEY_SECRET', '') or 'test_secret'
        signature = _make_razorpay_signature(
            payment.gateway_order_id, payment_id, secret
        )
        # The view does HMAC comparison inline (no external razorpay call for verify)
        resp = buyer_client.post(self.url, {
            'gateway_order_id': payment.gateway_order_id,
            'gateway_payment_id': payment_id,
            'gateway_signature': signature,
        })
        assert resp.status_code == status.HTTP_200_OK
        payment.refresh_from_db()
        assert payment.status == 'completed'

    def test_verify_invalid_signature(self, buyer_client, placed_order, buyer):
        self._create_payment(placed_order, buyer)
        resp = buyer_client.post(self.url, {
            'gateway_order_id': 'order_VERIFY_TEST',
            'gateway_payment_id': 'pay_FAKE',
            'gateway_signature': 'completely_wrong_sig',
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_verify_unknown_order_id(self, buyer_client, buyer):
        """Payment lookup is scoped to request.user — unknown order_id returns 404."""
        # We DON'T create a payment — just test the 404 path
        resp = buyer_client.post(self.url, {
            'gateway_order_id': 'order_DOES_NOT_EXIST_XYZ',
            'gateway_payment_id': 'pay_X',
            'gateway_signature': 'sig',
        })
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_verify_missing_fields(self, buyer_client):
        resp = buyer_client.post(self.url, {
            'razorpay_order_id': 'order_TEST',
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_verify_requires_auth(self, api_client, placed_order, buyer):
        self._create_payment(placed_order, buyer)
        resp = api_client.post(self.url, {
            'gateway_order_id': 'order_VERIFY_TEST',
            'gateway_payment_id': 'pay_X',
            'gateway_signature': 'sig',
        })
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# ─── Razorpay Webhook ─────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestRazorpayWebhook:
    url = '/api/payments/webhook/razorpay/'

    def _post_webhook(self, api_client, payload_dict, secret='test_secret'):
        body = json.dumps(payload_dict).encode()
        sig = _make_webhook_signature(body, secret)
        return api_client.post(
            self.url,
            data=body,
            content_type='application/json',
            HTTP_X_RAZORPAY_SIGNATURE=sig,
        )

    def test_payment_captured_event_marks_order_complete(
        self, api_client, placed_order, buyer
    ):
        from payments.models import Payment
        payment = Payment.objects.create(
            order=placed_order, user=buyer,
            payment_gateway='razorpay',
            gateway_order_id='order_WH_001',
            gateway_payment_id='pay_WH_001',
            amount=placed_order.total_price,
            currency='INR',
            status='pending',
        )
        payload = {
            'event': 'payment.captured',
            'payload': {
                'payment': {
                    'entity': {
                        'id': 'pay_WH_001',
                        'order_id': 'order_WH_001',
                        'amount': int(placed_order.total_price * 100),
                        'currency': 'INR',
                        'status': 'captured',
                    }
                }
            },
        }
        secret = settings.RAZORPAY_WEBHOOK_SECRET or 'test_secret'
        resp = self._post_webhook(api_client, payload, secret=secret)
        assert resp.status_code == status.HTTP_200_OK
        payment.refresh_from_db()
        assert payment.status == 'completed'
        placed_order.refresh_from_db()
        assert placed_order.payment_status == 'completed'

    def test_invalid_signature_rejected(self, api_client, placed_order, buyer):
        from payments.models import Payment
        Payment.objects.create(
            order=placed_order, user=buyer,
            payment_gateway='razorpay',
            gateway_order_id='order_BAD',
            amount=placed_order.total_price,
            currency='INR',
            status='pending',
        )
        body = json.dumps({'event': 'payment.captured'}).encode()
        resp = api_client.post(
            self.url,
            data=body,
            content_type='application/json',
            HTTP_X_RAZORPAY_SIGNATURE='bad_signature',
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_signature_header_rejected(self, api_client):
        body = json.dumps({'event': 'payment.captured'}).encode()
        resp = api_client.post(
            self.url, data=body, content_type='application/json',
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_unhandled_event_returns_200(self, api_client):
        """Unknown events must be acknowledged (200) but no state changes."""
        payload = {'event': 'some.unknown.event', 'payload': {}}
        secret = settings.RAZORPAY_WEBHOOK_SECRET or 'test_secret'
        resp = self._post_webhook(api_client, payload, secret=secret)
        assert resp.status_code == status.HTTP_200_OK

    def test_webhook_requires_no_auth(self, api_client):
        """Razorpay webhooks must be accepted without JWT auth."""
        payload = {'event': 'payment.captured', 'payload': {'payment': {'entity': {}}}}
        secret = settings.RAZORPAY_WEBHOOK_SECRET or 'test_secret'
        resp = self._post_webhook(api_client, payload, secret=secret)
        # 200 or 404/400 depending on entity — not 401
        assert resp.status_code != status.HTTP_401_UNAUTHORIZED


# ─── Payment Detail ───────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestPaymentDetail:

    def test_get_payment_detail(self, buyer_client, completed_payment, placed_order):
        resp = buyer_client.get(f'/api/payments/{placed_order.order_number}/')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['gateway_payment_id'] == completed_payment.gateway_payment_id

    def test_cannot_get_other_users_payment(self, buyer2_client, placed_order, completed_payment):
        resp = buyer2_client.get(f'/api/payments/{placed_order.order_number}/')
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_payment_detail_unauthenticated(self, api_client, placed_order):
        resp = api_client.get(f'/api/payments/{placed_order.order_number}/')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_payment_not_found(self, buyer_client):
        resp = buyer_client.get('/api/payments/SG-DOESNOTEXIST/')
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ─── Refund ───────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestRefund:

    def test_admin_can_create_refund(self, admin_client, placed_order, completed_payment):
        with patch('payments.views._get_razorpay_client') as mock_client_fn:
            mock_client = MagicMock()
            mock_client.payment.refund.return_value = {
                'id': 'rfnd_FAKE01',
                'amount': int(placed_order.total_price * 100),
                'status': 'processed',
            }
            mock_client_fn.return_value = mock_client
            resp = admin_client.post(
                f'/api/payments/{placed_order.order_number}/refund/',
                {'amount': str(placed_order.total_price), 'reason': 'Order cancelled by customer'},
            )
        assert resp.status_code == status.HTTP_201_CREATED

    def test_buyer_cannot_create_refund(self, buyer_client, placed_order, completed_payment):
        resp = buyer_client.post(
            f'/api/payments/{placed_order.order_number}/refund/',
            {'amount': str(placed_order.total_price)},
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_refund_requires_completed_payment(self, admin_client, placed_order):
        """Refund must fail if payment is not completed — get_object_or_404 returns 404."""
        resp = admin_client.post(
            f'/api/payments/{placed_order.order_number}/refund/',
            {'amount': str(placed_order.total_price)},
        )
        assert resp.status_code in (status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND)

    def test_refund_amount_exceeds_payment(self, admin_client, placed_order, completed_payment):
        with patch('payments.views._get_razorpay_client') as mock_client_fn:
            mock_client = MagicMock()
            mock_client.payment.refund.return_value = {'id': 'rfnd_FAKE02', 'status': 'processed'}
            mock_client_fn.return_value = mock_client
            resp = admin_client.post(
                f'/api/payments/{placed_order.order_number}/refund/',
                {'amount': '9999999.00', 'reason': 'Excess'},
            )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_refund_zero_amount_rejected(self, admin_client, placed_order, completed_payment):
        with patch('payments.views._get_razorpay_client') as mock_client_fn:
            mock_client = MagicMock()
            mock_client.payment.refund.return_value = {'id': 'rfnd_FAKE03', 'status': 'processed'}
            mock_client_fn.return_value = mock_client
            resp = admin_client.post(
                f'/api/payments/{placed_order.order_number}/refund/',
                {'amount': '0.00'},
            )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_refund_unauthenticated(self, api_client, placed_order):
        resp = api_client.post(
            f'/api/payments/{placed_order.order_number}/refund/',
            {'amount': '100.00'},
        )
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# ─── Payouts ─────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestPayouts:

    def _make_payout(self, payment, seller_profile, placed_order, status='pending'):
        """Helper — creates a SellerPayout with all required FKs."""
        from payments.models import SellerPayout
        order_item = placed_order.items.first()
        commission = (payment.amount * Decimal('10')) / Decimal('100')
        return SellerPayout.objects.create(
            payment=payment,
            seller=seller_profile,
            order_item=order_item,
            gross_amount=payment.amount,
            platform_commission=commission,
            seller_amount=payment.amount - commission,
            payout_status=status,
        )

    def test_admin_can_list_payouts(self, admin_client, completed_payment,
                                    seller_profile, placed_order):
        self._make_payout(completed_payment, seller_profile, placed_order)
        resp = admin_client.get('/api/payments/payouts/')
        assert resp.status_code == status.HTTP_200_OK
        # Admin payout list returns a plain list
        assert len(resp.data) >= 1

    def test_buyer_cannot_list_payouts(self, buyer_client):
        resp = buyer_client.get('/api/payments/payouts/')
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_seller_can_list_own_payouts(self, seller_client, completed_payment,
                                         seller_profile, placed_order):
        self._make_payout(completed_payment, seller_profile, placed_order)
        resp = seller_client.get('/api/payments/payouts/seller/')
        assert resp.status_code == status.HTTP_200_OK
        # Seller payout list returns a plain list
        assert len(resp.data) >= 1

    def test_seller2_cannot_see_seller1_payouts(self, seller2_client, completed_payment,
                                                seller_profile, placed_order):
        self._make_payout(completed_payment, seller_profile, placed_order)
        resp = seller2_client.get('/api/payments/payouts/seller/')
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) == 0

    def test_admin_can_process_payout(self, admin_client, completed_payment,
                                      seller_profile, placed_order):
        payout = self._make_payout(completed_payment, seller_profile, placed_order)
        # The process endpoint is PATCH and requires 'payout_reference' field
        resp = admin_client.patch(
            f'/api/payments/payouts/{payout.id}/process/',
            {'payout_reference': 'UTR123456'},
        )
        assert resp.status_code == status.HTTP_200_OK
        payout.refresh_from_db()
        assert payout.payout_status in ('processed', 'completed')

    def test_buyer_cannot_process_payout(self, buyer_client, completed_payment,
                                         seller_profile, placed_order):
        payout = self._make_payout(completed_payment, seller_profile, placed_order)
        resp = buyer_client.patch(
            f'/api/payments/payouts/{payout.id}/process/',
            {'payout_reference': 'HACK'},
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_process_already_processed_payout(self, admin_client, completed_payment,
                                              seller_profile, placed_order):
        payout = self._make_payout(completed_payment, seller_profile, placed_order,
                                   status='completed')
        resp = admin_client.patch(
            f'/api/payments/payouts/{payout.id}/process/',
            {'payout_reference': 'UTR99'},
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_payout_auto_created_on_payment_capture(
        self, api_client, placed_order, buyer, seller_profile
    ):
        """
        Capturing payment via webhook must auto-create SellerPayout records
        for each order_item tied to a seller.
        """
        from payments.models import Payment, SellerPayout
        Payment.objects.create(
            order=placed_order, user=buyer,
            payment_gateway='razorpay',
            gateway_order_id='order_AUTO_PAY',
            gateway_payment_id='pay_AUTO_PAY',
            amount=placed_order.total_price,
            currency='INR',
            status='pending',
        )
        payload = {
            'event': 'payment.captured',
            'payload': {
                'payment': {
                    'entity': {
                        'id': 'pay_AUTO_PAY',
                        'order_id': 'order_AUTO_PAY',
                        'amount': int(placed_order.total_price * 100),
                        'currency': 'INR',
                        'status': 'captured',
                    }
                }
            },
        }
        body = json.dumps(payload).encode()
        secret = settings.RAZORPAY_WEBHOOK_SECRET or 'test_secret'
        sig = _make_webhook_signature(body, secret)
        api_client.post(
            '/api/payments/webhook/razorpay/',
            data=body,
            content_type='application/json',
            HTTP_X_RAZORPAY_SIGNATURE=sig,
        )
        assert SellerPayout.objects.filter(
            seller=seller_profile,
            order_item__order=placed_order,
        ).exists()
