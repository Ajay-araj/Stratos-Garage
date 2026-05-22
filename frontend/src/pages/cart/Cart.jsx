import React, { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Trash2, Loader2, ShoppingBag } from 'lucide-react';
import api from '../../services/api';
import useCartStore from '../../store/useCartStore';
import useAuthStore from '../../store/useAuthStore';
import { formatINR } from '../../utils/currency';
import GlassCard from '../../components/ui/GlassCard';
import Button from '../../components/ui/Button';

export default function Cart() {
  const { user } = useAuthStore();
  const { setItemCount } = useCartStore();

  const [cart, setCart]       = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);
  const [updatingId, setUpdatingId] = useState(null);

  // ── Fetch cart from backend ───────────────────────────────────────────────
  const fetchCart = useCallback(async () => {
    if (!user) { setLoading(false); return; }
    try {
      setLoading(true);
      setError(null);
      const res = await api.get('orders/cart/');
      setCart(res.data);
      setItemCount(res.data.item_count ?? 0);
    } catch {
      setError('Failed to load cart. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [user, setItemCount]);

  useEffect(() => { fetchCart(); }, [fetchCart]);

  // ── Actions ───────────────────────────────────────────────────────────────
  const handleRemove = async (itemId) => {
    setUpdatingId(itemId);
    try {
      await api.delete(`orders/cart/${itemId}/`);
      await fetchCart();
    } catch {
      alert('Failed to remove item.');
    } finally {
      setUpdatingId(null);
    }
  };

  const handleQuantityChange = async (itemId, newQty) => {
    if (newQty < 1) return;
    setUpdatingId(itemId);
    try {
      await api.patch(`orders/cart/${itemId}/`, { quantity: newQty });
      await fetchCart();
    } catch (err) {
      alert(err.response?.data?.error || 'Failed to update quantity.');
      await fetchCart(); // re-sync with real backend state
    } finally {
      setUpdatingId(null);
    }
  };

  // ── Guard: not logged in ──────────────────────────────────────────────────
  if (!user) {
    return (
      <div className="p-8 max-w-7xl mx-auto pt-24 min-h-screen">
        <h1 className="text-4xl font-display font-bold text-white mb-8">SHOPPING CART</h1>
        <GlassCard className="p-12 text-center">
          <ShoppingBag size={48} className="text-gray-600 mb-4 mx-auto" />
          <p className="text-gray-400 mb-6 text-xl">Please log in to view your cart.</p>
          <Link to="/login"><Button variant="primary">LOGIN</Button></Link>
        </GlassCard>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="p-8 max-w-7xl mx-auto pt-24 min-h-screen flex items-center justify-center">
        <Loader2 className="animate-spin text-white" size={48} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 max-w-7xl mx-auto pt-24 min-h-screen">
        <h1 className="text-4xl font-display font-bold text-white mb-8">SHOPPING CART</h1>
        <GlassCard className="p-12 text-center">
          <p className="text-red-400 mb-6">{error}</p>
          <Button variant="secondary" onClick={fetchCart}>Retry</Button>
        </GlassCard>
      </div>
    );
  }

  const items          = cart?.items ?? [];
  const subtotal       = parseFloat(cart?.subtotal ?? 0);
  const total          = parseFloat(cart?.total ?? 0);
  const discountAmount = parseFloat(cart?.discount_amount ?? 0);

  return (
    <div className="p-8 max-w-7xl mx-auto pt-24 min-h-screen">
      <h1 className="text-4xl font-display font-bold text-white mb-8">SHOPPING CART</h1>

      {items.length === 0 ? (
        <GlassCard className="p-12 text-center">
          <ShoppingBag size={48} className="text-gray-600 mb-4 mx-auto" />
          <p className="text-gray-400 mb-6 text-xl">Your cart is empty.</p>
          <Link to="/products"><Button variant="primary">CONTINUE SHOPPING</Button></Link>
        </GlassCard>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

          {/* ── Cart Items ── */}
          <div className="lg:col-span-2 space-y-4">
            {items.map((item) => {
              const isUpdating = updatingId === item.id;
              const imgSrc = item.thumbnail_url || 'https://via.placeholder.com/100?text=No+Image';
              const attrs  = item.variant?.attributes ?? [];

              return (
                <GlassCard
                  key={item.id}
                  className={`p-4 flex gap-4 items-center transition-opacity ${isUpdating ? 'opacity-50 pointer-events-none' : ''}`}
                >
                  <div className="w-24 h-24 bg-gray-900 rounded overflow-hidden flex-shrink-0">
                    <img src={imgSrc} alt={item.product_name} className="w-full h-full object-cover" />
                  </div>

                  <div className="flex-grow min-w-0">
                    <h3 className="text-lg font-bold text-white truncate">{item.product_name}</h3>
                    {attrs.length > 0 && (
                      <p className="text-xs text-gray-500 mt-0.5">
                        {attrs.map(a => `${a.attribute_type_name}: ${a.value}`).join(' · ')}
                      </p>
                    )}
                    <p className="text-gray-400 mt-1">{formatINR(item.variant?.price ?? 0)}</p>
                    <p className="text-xs text-gray-600 mt-0.5">Subtotal: {formatINR(item.subtotal)}</p>
                  </div>

                  <div className="flex items-center gap-3 flex-shrink-0">
                    <input
                      type="number"
                      min="1"
                      value={item.quantity}
                      disabled={isUpdating}
                      onChange={(e) => handleQuantityChange(item.id, parseInt(e.target.value) || 1)}
                      className="w-16 bg-black border border-white/20 text-white px-2 py-1 rounded outline-none text-center disabled:opacity-50"
                    />
                    <button
                      onClick={() => handleRemove(item.id)}
                      disabled={isUpdating}
                      className="text-gray-500 hover:text-red-500 transition-colors disabled:opacity-50"
                    >
                      <Trash2 size={20} />
                    </button>
                  </div>
                </GlassCard>
              );
            })}
          </div>

          {/* ── Order Summary ── */}
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
            <GlassCard className="p-6 sticky top-24">
              <h3 className="text-xl font-bold text-white mb-4 border-b border-white/10 pb-4">ORDER SUMMARY</h3>

              <div className="space-y-2 mb-4">
                <div className="flex justify-between text-gray-300">
                  <span>Subtotal ({items.length} {items.length === 1 ? 'item' : 'items'})</span>
                  <span>{formatINR(subtotal)}</span>
                </div>
                {discountAmount > 0 && (
                  <div className="flex justify-between text-green-400">
                    <span>Discount</span>
                    <span>-{formatINR(discountAmount)}</span>
                  </div>
                )}
                <div className="flex justify-between text-gray-300 border-b border-white/10 pb-4">
                  <span>Shipping</span>
                  <span>Calculated at checkout</span>
                </div>
              </div>

              <div className="flex justify-between text-white font-bold text-xl mb-6">
                <span>Total</span>
                <span>{formatINR(total)}</span>
              </div>

              <Link to="/checkout">
                <Button variant="primary" className="w-full">PROCEED TO CHECKOUT</Button>
              </Link>
            </GlassCard>
          </motion.div>

        </div>
      )}
    </div>
  );
}
