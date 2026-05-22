import React, { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../../services/api';
import useCartStore from '../../store/useCartStore';
import GlassCard from '../../components/ui/GlassCard';
import Button from '../../components/ui/Button';
import PaymentModal from '../../components/payment/PaymentModal';
import { formatINR } from '../../utils/currency';
import { CreditCard, Truck, Wallet, FileText, Calendar } from 'lucide-react';

export default function Checkout() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const clearCart = useCartStore((state) => state.clearCount);

  const [checkoutData, setCheckoutData] = useState({
    shipping_name: '',
    shipping_phone: '',
    shipping_address_line1: '',
    shipping_address_line2: '',
    city: '',
    district: '',
    state: '',
    postal_code: '',
    country: 'India',
  });

  const [paymentMethod, setPaymentMethod] = useState('razorpay');
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [pendingShipping, setPendingShipping] = useState(null);
  const [demoOrderId] = useState(() => `SG-${Date.now().toString(36).toUpperCase()}`);
  const [pinLoading, setPinLoading] = useState(false);
  const [pinSuccess, setPinSuccess] = useState(false);
  const [pinError, setPinError] = useState('');

  // ── Pincode autofill ──────────────────────────────────────────────────────
  const fetchLocationByPincode = useCallback(async (pincode) => {
    if (!pincode || pincode.length !== 6) return;

    setPinLoading(true);
    setPinSuccess(false);
    setPinError('');

    try {
      const response = await fetch(`https://api.postalpincode.in/pincode/${pincode}`);
      const result = await response.json();

      if (result && result[0] && result[0].Status === 'Success') {
        const office = result[0].PostOffice[0];
        // Use functional update so we never read stale state
        setCheckoutData((prev) => ({
          ...prev,
          city: office.Name || '',
          district: office.District || '',
          state: office.State || '',
          country: office.Country || 'India',
        }));
        setPinSuccess(true);
      } else {
        console.warn('Invalid PIN code:', pincode);
        setPinSuccess(false);
      }
    } catch (error) {
      console.error('Pincode fetch failed:', error);
    } finally {
      setPinLoading(false);
    }
  }, []);

  // ── Cart data ─────────────────────────────────────────────────────────────
  const { data: cart, isLoading } = useQuery({
    queryKey: ['cart'],
    queryFn: () => api.get('orders/cart/').then((res) => res.data),
  });

  // ── Place-order mutation ───────────────────────────────────────────────────
  const placeOrderMutation = useMutation({
    mutationFn: (data) => api.post('orders/place/', data),
    onError: () => {
      setShowPaymentModal(false);
      alert('Unable to place order. Please try again.');
    },
  });

  // ── QR payment flow ───────────────────────────────────────────────────────
  const handlePaymentConfirmed = async () => {
    if (!pendingShipping) return;
    try {
      const res = await placeOrderMutation.mutateAsync(pendingShipping);
      const orderNumber = res.data?.order?.order_number;

      if (orderNumber) {
        try {
          await api.post(`orders/${orderNumber}/mark-paid/`);
        } catch (payErr) {
          console.error('mark-paid failed:', payErr?.response?.data || payErr);
          try { await api.post(`orders/${orderNumber}/mark-paid/`); } catch (_) {}
        }
      }

      queryClient.invalidateQueries(['cart']);
      queryClient.invalidateQueries(['orders']);
      clearCart();
      navigate('/orders/success', { state: { orderId: orderNumber || demoOrderId } });
    } catch (err) {
      console.error('Order placement failed:', err?.response?.data || err);
    }
  };

  // ── Input handler (functional update to avoid stale closure) ──────────────
  const handleInputChange = useCallback((e) => {
    const { name, value } = e.target;
    setCheckoutData((prev) => ({ ...prev, [name]: value }));
  }, []);

  // ── Pincode input: update state then trigger fetch ─────────────────────────
  const handlePincodeChange = useCallback((e) => {
    const value = e.target.value.replace(/\D/g, '').slice(0, 6);
    setCheckoutData((prev) => ({ ...prev, postal_code: value }));
    if (value.length === 6) {
      fetchLocationByPincode(value);
    } else {
      setPinSuccess(false);
      setPinError('');
    }
  }, [fetchLocationByPincode]);

  // ── Form submit ───────────────────────────────────────────────────────────
  const handleSubmit = (e) => {
    e.preventDefault();

    const payload = {
      shipping_name: checkoutData.shipping_name,
      shipping_phone: checkoutData.shipping_phone,
      shipping_address_line1: checkoutData.shipping_address_line1,
      shipping_address_line2: checkoutData.shipping_address_line2,
      shipping_city: checkoutData.city,
      shipping_state: checkoutData.state,
      shipping_pincode: checkoutData.postal_code,
      shipping_country: checkoutData.country,
    };

    if (paymentMethod === 'razorpay') {
      setPendingShipping(payload);
      setShowPaymentModal(true);
    } else {
      // COD flow
      placeOrderMutation.mutate(payload, {
        onSuccess: (res) => {
          queryClient.invalidateQueries(['cart']);
          queryClient.invalidateQueries(['orders']);
          clearCart();
          alert('Order Placed Successfully');
          navigate('/orders');
        },
      });
    }
  };

  // ── Guards ────────────────────────────────────────────────────────────────
  if (isLoading) {
    return <div className="p-8 text-center text-white pt-24">Loading checkout...</div>;
  }
  if (!cart || cart.items.length === 0) {
    return (
      <div className="p-8 max-w-4xl mx-auto pt-24 min-h-screen text-center flex flex-col items-center justify-center">
        <GlassCard className="p-12 w-full">
          <h1 className="text-3xl font-bold text-white mb-4 uppercase tracking-widest">Cart is Empty</h1>
          <p className="text-gray-400 mb-8 font-light">Add items to your cart before proceeding to checkout.</p>
          <Button variant="primary" onClick={() => navigate('/products')} className="px-8 py-3">VIEW PRODUCTS</Button>
        </GlassCard>
      </div>
    );
  }

  const expectedDelivery = new Date();
  expectedDelivery.setDate(expectedDelivery.getDate() + 5);

  return (
    <div className="p-8 max-w-6xl mx-auto pt-24 min-h-screen">
      <h1 className="text-4xl font-display font-bold text-white mb-10 tracking-widest uppercase">Checkout</h1>

      {showPaymentModal && (
        <PaymentModal
          amount={cart.total}
          orderId={demoOrderId}
          onConfirm={handlePaymentConfirmed}
          onClose={() => setShowPaymentModal(false)}
          isPlacing={placeOrderMutation.isPending}
        />
      )}

      <form onSubmit={handleSubmit} className="grid grid-cols-1 lg:grid-cols-3 gap-8">

        {/* Left Column */}
        <div className="lg:col-span-2 space-y-8">

          {/* Shipping Address */}
          <GlassCard className="p-8">
            <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
              <Truck className="text-gray-400" /> Shipping Address
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

              <div className="space-y-2">
                <label className="text-xs uppercase tracking-widest text-gray-400">Full Name</label>
                <input
                  required
                  name="shipping_name"
                  value={checkoutData.shipping_name}
                  onChange={handleInputChange}
                  type="text"
                  className="w-full bg-black/50 border border-white/10 rounded p-3 text-white focus:border-white/50 outline-none"
                />
              </div>

              <div className="space-y-2">
                <label className="text-xs uppercase tracking-widest text-gray-400">Phone Number</label>
                <input
                  required
                  name="shipping_phone"
                  value={checkoutData.shipping_phone}
                  onChange={handleInputChange}
                  type="tel"
                  className="w-full bg-black/50 border border-white/10 rounded p-3 text-white focus:border-white/50 outline-none"
                />
              </div>

              <div className="space-y-2 md:col-span-2">
                <label className="text-xs uppercase tracking-widest text-gray-400">Address Line 1</label>
                <input
                  required
                  name="shipping_address_line1"
                  value={checkoutData.shipping_address_line1}
                  onChange={handleInputChange}
                  type="text"
                  className="w-full bg-black/50 border border-white/10 rounded p-3 text-white focus:border-white/50 outline-none"
                />
              </div>

              <div className="space-y-2 md:col-span-2">
                <label className="text-xs uppercase tracking-widest text-gray-400">Address Line 2 (Optional)</label>
                <input
                  name="shipping_address_line2"
                  value={checkoutData.shipping_address_line2}
                  onChange={handleInputChange}
                  type="text"
                  className="w-full bg-black/50 border border-white/10 rounded p-3 text-white focus:border-white/50 outline-none"
                />
              </div>

              {/* Postal Code — dedicated handler */}
              <div className="space-y-2 relative">
                <label className="text-xs uppercase tracking-widest text-gray-400">Postal Code</label>
                <div className="relative">
                  <input
                    required
                    name="postal_code"
                    maxLength={6}
                    value={checkoutData.postal_code}
                    onChange={handlePincodeChange}
                    type="text"
                    inputMode="numeric"
                    placeholder="6-digit PIN"
                    className={`w-full bg-black/50 border ${
                      pinError ? 'border-red-500' : pinSuccess ? 'border-green-500' : 'border-white/10'
                    } rounded p-3 text-white focus:border-white/50 outline-none transition-colors`}
                  />
                  {pinLoading && (
                    <div className="absolute right-3 top-3 animate-spin rounded-full h-5 w-5 border-t-2 border-b-2 border-white" />
                  )}
                  {pinSuccess && !pinLoading && (
                    <div className="absolute right-3 top-3 text-green-500 font-bold">✓</div>
                  )}
                </div>
                {pinError && <p className="text-red-500 text-xs mt-1">{pinError}</p>}
              </div>

              {/* City — bound to checkoutData.city */}
              <div className="space-y-2">
                <label className="text-xs uppercase tracking-widest text-gray-400">City / Town</label>
                <input
                  required
                  name="city"
                  value={checkoutData.city}
                  onChange={handleInputChange}
                  type="text"
                  placeholder="Auto-filled from PIN"
                  className="w-full bg-black/50 border border-white/10 rounded p-3 text-white focus:border-white/50 outline-none"
                />
              </div>

              {/* District — bound to checkoutData.district */}
              <div className="space-y-2">
                <label className="text-xs uppercase tracking-widest text-gray-400">District</label>
                <input
                  required
                  name="district"
                  value={checkoutData.district}
                  onChange={handleInputChange}
                  type="text"
                  placeholder="Auto-filled from PIN"
                  className="w-full bg-black/50 border border-white/10 rounded p-3 text-white focus:border-white/50 outline-none"
                />
              </div>

              {/* State — bound to checkoutData.state */}
              <div className="space-y-2">
                <label className="text-xs uppercase tracking-widest text-gray-400">State</label>
                <input
                  required
                  name="state"
                  value={checkoutData.state}
                  onChange={handleInputChange}
                  type="text"
                  placeholder="Auto-filled from PIN"
                  className="w-full bg-black/50 border border-white/10 rounded p-3 text-white focus:border-white/50 outline-none"
                />
              </div>

              {/* Country — bound to checkoutData.country */}
              <div className="space-y-2 md:col-span-2">
                <label className="text-xs uppercase tracking-widest text-gray-400">Country</label>
                <input
                  required
                  name="country"
                  value={checkoutData.country}
                  onChange={handleInputChange}
                  type="text"
                  className="w-full bg-black/50 border border-white/10 rounded p-3 text-white focus:border-white/50 outline-none"
                />
              </div>

            </div>
          </GlassCard>

          {/* Payment Method */}
          <GlassCard className="p-8">
            <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
              <Wallet className="text-gray-400" /> Payment Method
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <label className={`cursor-pointer p-4 border rounded flex items-center gap-3 transition-colors ${
                paymentMethod === 'razorpay' ? 'border-white bg-white/10' : 'border-white/10 hover:border-white/30 bg-black/50'
              }`}>
                <input type="radio" name="paymentMethod" value="razorpay" checked={paymentMethod === 'razorpay'} onChange={() => setPaymentMethod('razorpay')} className="hidden" />
                <CreditCard className={paymentMethod === 'razorpay' ? 'text-white' : 'text-gray-500'} />
                <div className="flex-1">
                  <div className={`font-bold ${paymentMethod === 'razorpay' ? 'text-white' : 'text-gray-400'}`}>Razorpay</div>
                  <div className="text-xs text-gray-500">Cards, UPI, NetBanking</div>
                </div>
              </label>

              <label className={`cursor-pointer p-4 border rounded flex items-center gap-3 transition-colors ${
                paymentMethod === 'cod' ? 'border-white bg-white/10' : 'border-white/10 hover:border-white/30 bg-black/50'
              }`}>
                <input type="radio" name="paymentMethod" value="cod" checked={paymentMethod === 'cod'} onChange={() => setPaymentMethod('cod')} className="hidden" />
                <Wallet className={paymentMethod === 'cod' ? 'text-white' : 'text-gray-500'} />
                <div className="flex-1">
                  <div className={`font-bold ${paymentMethod === 'cod' ? 'text-white' : 'text-gray-400'}`}>Cash on Delivery</div>
                  <div className="text-xs text-gray-500">Pay when you receive</div>
                </div>
              </label>
            </div>
          </GlassCard>
        </div>

        {/* Right Column — Order Summary */}
        <div className="space-y-8">
          <GlassCard className="p-8 sticky top-24">
            <h2 className="text-xl font-bold text-white mb-6 flex items-center gap-3 border-b border-white/10 pb-4">
              <FileText className="text-gray-400" size={20} /> Order Summary
            </h2>

            <div className="space-y-4 mb-6">
              {cart.items.map((item) => (
                <div key={item.id} className="flex gap-4 items-center">
                  <div className="w-12 h-12 bg-gray-900 rounded overflow-hidden flex-shrink-0">
                    <img
                      src={item.thumbnail_url || 'https://via.placeholder.com/100'}
                      alt={item.product_name}
                      className="w-full h-full object-cover"
                    />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-bold text-white truncate">{item.product_name}</div>
                    <div className="text-xs text-gray-500">Qty: {item.quantity}</div>
                  </div>
                  <div className="text-sm text-white font-bold">{formatINR(item.subtotal)}</div>
                </div>
              ))}
            </div>

            <div className="space-y-3 pt-6 border-t border-white/10 mb-6">
              <div className="flex justify-between text-gray-400 text-sm">
                <span>Subtotal</span>
                <span className="text-white">{formatINR(cart.subtotal)}</span>
              </div>
              <div className="flex justify-between text-gray-400 text-sm">
                <span>Shipping</span>
                <span className="text-white">Free</span>
              </div>
              {cart.discount_amount > 0 && (
                <div className="flex justify-between text-green-400 text-sm">
                  <span>Discount</span>
                  <span>-{formatINR(cart.discount_amount)}</span>
                </div>
              )}
            </div>

            <div className="flex justify-between text-white font-display text-2xl font-bold pt-6 border-t border-white/10 mb-8">
              <span>Total</span>
              <span>{formatINR(cart.total)}</span>
            </div>

            <div className="bg-white/5 border border-white/10 rounded-lg p-4 mb-8 flex items-center gap-3">
              <Calendar className="text-gray-400 flex-shrink-0" />
              <div>
                <div className="text-xs text-gray-400 uppercase tracking-widest">Expected Delivery</div>
                <div className="text-white font-bold">
                  {expectedDelivery.toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' })}
                </div>
              </div>
            </div>

            <Button
              type="submit"
              variant="primary"
              className="w-full py-4 text-sm disabled:opacity-50"
              disabled={placeOrderMutation.isPending}
            >
              {placeOrderMutation.isPending
                ? 'PROCESSING...'
                : paymentMethod === 'cod'
                  ? 'PLACE ORDER'
                  : `PAY ${formatINR(cart.total)}`}
            </Button>

            {paymentMethod === 'cod' && (
              <div className="mt-3 text-center text-xs text-gray-500 flex items-center justify-center gap-2">
                <Wallet size={12} className="text-gray-600" />
                <span>You will pay cash when your order is delivered</span>
              </div>
            )}
          </GlassCard>
        </div>
      </form>
    </div>
  );
}
