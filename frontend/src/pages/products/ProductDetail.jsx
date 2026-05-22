import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import api from '../../services/api';
import useCartStore from '../../store/useCartStore';
import useAuthStore from '../../store/useAuthStore';
import Button from '../../components/ui/Button';
import GlassCard from '../../components/ui/GlassCard';
import { formatINR } from '../../utils/currency';
import { motion } from 'framer-motion';
import { ShoppingCart, Zap, Check, Heart } from 'lucide-react';

export default function ProductDetail() {
  const { id } = useParams();
  const { user } = useAuthStore();
  const { incrementCount } = useCartStore();
  const [quantity, setQuantity] = useState(1);
  const [selectedVariantIdx, setSelectedVariantIdx] = useState(0);
  const [addStatus, setAddStatus] = useState(null); // null | 'adding' | 'success' | 'error'
  const [inWishlist, setInWishlist] = useState(false);
  const [wishlistLoading, setWishlistLoading] = useState(false);
  const navigate = useNavigate();

  const { data: product, isLoading, isError } = useQuery({
    queryKey: ['product', id],
    queryFn: () => api.get(`products/${id}/`).then(res => res.data),
    retry: false,
  });

  React.useEffect(() => {
    if (user && product) {
      api.get(`/wishlist/check/?product_id=${product.id}`).then(res => {
        setInWishlist(res.data.in_wishlist);
      }).catch(console.error);
    }
  }, [user, product]);

  const activeVariants = product?.variants?.filter(v => v.is_active) ?? [];
  const selectedVariant = activeVariants[selectedVariantIdx] ?? null;
  const displayPrice = selectedVariant?.price ?? product?.price;

  const addToBackendCart = async () => {
    if (!user) { navigate('/login'); return false; }
    
    const payload = { quantity };
    if (selectedVariant) {
        payload.variant_id = selectedVariant.id;
    } else {
        payload.product_id = product.id;
    }
    
    await api.post('orders/cart/add/', payload);
    incrementCount();
    return true;
  };

  const handleAddToCart = async () => {
    setAddStatus('adding');
    try {
      await addToBackendCart();
      setAddStatus('success');
      setTimeout(() => setAddStatus(null), 2000);
    } catch (err) {
      setAddStatus('error');
      alert(err.response?.data?.error || 'Failed to add to cart.');
      setTimeout(() => setAddStatus(null), 2000);
    }
  };

  const handleBuyNow = async () => {
    try {
      const ok = await addToBackendCart();
      if (ok) navigate('/checkout');
    } catch (err) {
      alert(err.response?.data?.error || 'Failed to add to cart.');
    }
  };

  const handleToggleWishlist = async () => {
    if (!user) {
      navigate('/login');
      return;
    }
    setWishlistLoading(true);
    try {
      if (inWishlist) {
        await api.delete(`/wishlist/${product.id}/`);
        setInWishlist(false);
      } else {
        await api.post('/wishlist/add/', { product_id: product.id });
        setInWishlist(true);
      }
    } catch (err) {
      alert('Failed to update wishlist.');
    } finally {
      setWishlistLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="p-8 max-w-7xl mx-auto pt-24 min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-white"></div>
      </div>
    );
  }

  if (isError || !product) {
    return (
      <div className="p-8 max-w-7xl mx-auto pt-24 min-h-screen flex items-center justify-center">
        <GlassCard className="p-12 text-center">
          <h2 className="text-2xl font-bold text-red-400 mb-4">Product Not Found</h2>
          <p className="text-gray-400 mb-6">The product you are looking for does not exist or has been removed.</p>
          <Button variant="primary" onClick={() => navigate('/products')}>BROWSE PRODUCTS</Button>
        </GlassCard>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-7xl mx-auto pt-24 min-h-screen">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
        <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}>
          <GlassCard className="aspect-square bg-gray-900 overflow-hidden rounded-xl">
            <img
              src={product?.image || 'https://via.placeholder.com/800?text=No+Image'}
              alt={product?.name}
              className="w-full h-full object-cover"
            />
          </GlassCard>
        </motion.div>

        <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} className="space-y-6">
          <div className="flex justify-between items-start">
            <h1 className="text-4xl font-display font-bold text-white">{product?.name}</h1>
            <button 
              onClick={handleToggleWishlist}
              disabled={wishlistLoading}
              className={`p-3 rounded-full transition-colors ${inWishlist ? 'bg-red-500/20 text-red-500 hover:bg-red-500/30' : 'bg-white/5 text-gray-400 hover:bg-white/10 hover:text-white'}`}
            >
              <Heart size={24} className={inWishlist ? 'fill-current' : ''} />
            </button>
          </div>
          <p className="text-2xl text-gray-300">{formatINR(displayPrice)}</p>
          <p className="text-gray-400 leading-relaxed">{product?.description}</p>

          {/* Variant selector */}
          {activeVariants.length > 1 && (
            <div>
              <div className="text-xs text-gray-400 uppercase tracking-widest mb-2">Select Variant</div>
              <div className="flex flex-wrap gap-2">
                {activeVariants.map((v, idx) => (
                  <button
                    key={v.id}
                    onClick={() => setSelectedVariantIdx(idx)}
                    className={`px-3 py-1.5 text-xs border rounded transition-colors ${
                      idx === selectedVariantIdx
                        ? 'border-white bg-white text-black font-bold'
                        : 'border-white/20 text-gray-300 hover:border-white/50'
                    }`}
                  >
                    {v.attributes?.map(a => a.value).join(' / ') || v.sku}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="pt-6 border-t border-white/10">
            <div className="flex items-center gap-4 mb-6">
              <span className="text-white text-sm uppercase tracking-widest">Quantity:</span>
              <input
                type="number"
                min="1"
                max={selectedVariant?.available_quantity ?? 99}
                value={quantity}
                onChange={e => setQuantity(Math.max(1, parseInt(e.target.value) || 1))}
                className="bg-black border border-white/20 text-white px-3 py-2 rounded w-20 outline-none focus:border-white/50"
              />
            </div>

            <div className="flex gap-4 mt-8">
              <Button
                variant="secondary"
                className="flex-1 py-3 flex items-center justify-center gap-2"
                onClick={handleAddToCart}
                disabled={addStatus === 'adding'}
              >
                {addStatus === 'success' ? (
                  <><Check size={16} /> ADDED!</>
                ) : addStatus === 'adding' ? (
                  'ADDING...'
                ) : (
                  <><ShoppingCart size={16} /> ADD TO CART</>
                )}
              </Button>
              <Button
                variant="primary"
                className="flex-1 py-3 flex items-center justify-center gap-2"
                onClick={handleBuyNow}
                disabled={addStatus === 'adding'}
              >
                <Zap size={16} /> BUY NOW
              </Button>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
