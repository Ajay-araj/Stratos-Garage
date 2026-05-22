from rest_framework import serializers
from .models import Payment, Refund, SellerPayout


class PaymentSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source='order.order_number', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'order_number', 'payment_gateway', 'gateway_order_id',
            'gateway_payment_id', 'amount', 'currency', 'status',
            'payment_method', 'failure_reason', 'initiated_at', 'completed_at',
        ]
        read_only_fields = ['id', 'initiated_at', 'completed_at']


class PaymentInitiateSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
    # phonepe is not yet implemented \u2014 keep choices in sync with view logic
    payment_gateway = serializers.ChoiceField(choices=['razorpay', 'cod'])


class PaymentVerifySerializer(serializers.Serializer):
    gateway_order_id = serializers.CharField()
    gateway_payment_id = serializers.CharField(required=False, allow_blank=True, default='')
    gateway_signature = serializers.CharField(required=False, allow_blank=True, default='')


class RefundSerializer(serializers.ModelSerializer):
    """
    `payment`, `gateway_refund_id`, and `status` are set by the view via
    serializer.save() kwargs — never supplied by the client.
    `payment` is read_only so validation does not require it in the request body;
    it is still injected correctly via save(payment=payment).
    """
    class Meta:
        model = Refund
        fields = [
            'id', 'payment', 'order_item', 'amount', 'reason',
            'gateway_refund_id', 'status', 'initiated_at', 'completed_at',
        ]
        read_only_fields = ['id', 'payment', 'initiated_at', 'completed_at']
        extra_kwargs = {
            # Server-set fields — not required in client payload
            'gateway_refund_id': {'required': False},
            'status': {'required': False},
            'order_item': {'required': False, 'allow_null': True},
        }

    def validate_amount(self, value):
        from decimal import Decimal
        if value <= Decimal('0'):
            raise serializers.ValidationError("Refund amount must be greater than zero.")
        # Access the payment being refunded from view context
        payment = self.context.get('payment')
        if payment:
            if value > payment.amount:
                raise serializers.ValidationError(
                    f"Refund amount ({value}) cannot exceed payment amount ({payment.amount})."
                )
        return value


class SellerPayoutSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source='seller.store_name', read_only=True)
    product_name = serializers.CharField(source='order_item.product_name', read_only=True)

    class Meta:
        model = SellerPayout
        fields = [
            'id', 'store_name', 'product_name', 'gross_amount',
            'platform_commission', 'seller_amount', 'payout_status',
            'payout_reference', 'payout_date', 'created_at',
        ]
        read_only_fields = ['id', 'gross_amount', 'platform_commission', 'seller_amount', 'created_at']
