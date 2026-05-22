import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';
import api from '../../services/api';
import GlassCard from '../../components/ui/GlassCard';
import { motion } from 'framer-motion';
import { ShoppingCart, CreditCard, Heart } from 'lucide-react';
import useCartStore from '../../store/useCartStore';
import useAuthStore from '../../store/useAuthStore';
import { formatINR } from '../../utils/currency';

export default function ProductList() {
  const [searchParams] = useSearchParams();
  const searchParam = searchParams.get('q');
  const categoryParam = searchParams.get('category');
  const navigate = useNavigate();

  React.useEffect(() => {
    if (categoryParam) {
      navigate(`/shop/${categoryParam}`, { replace: true });
    }
  }, [categoryParam, navigate]);
  
  const { data, isLoading } = useQuery({
    queryKey: ['products', searchParam, categoryParam],
    queryFn: () => api.get('products/', {
      params: {
        q: searchParam || undefined,
        category: categoryParam || undefined,
      }
    }).then(res => res.data)
  });
  
  const { user } = useAuthStore();
  
  const { data: wishlistData, refetch: refetchWishlist } = useQuery({
    queryKey: ['wishlist'],
    queryFn: () => api.get('wishlist/').then(res => res.data),
    enabled: !!user,
  });
  
  const wishlistProductIds = new Set(wishlistData?.items?.map(item => item.product.id) || []);
  
  const handleToggleWishlist = async (e, product) => {
    e.preventDefault();
    if (!user) {
      navigate('/login');
      return;
    }
    const inWishlist = wishlistProductIds.has(product.id);
    try {
      if (inWishlist) {
        await api.delete(`/wishlist/${product.id}/`);
      } else {
        await api.post('/wishlist/add/', { product_id: product.id });
      }
      refetchWishlist();
    } catch (err) {
      console.error(err);
    }
  };

  const handleBuyNow = (e, product) => {
    e.preventDefault();
    navigate(`/products/${product.slug}`);
  };

  const handleAddToCart = (e, product) => {
    e.preventDefault();
    navigate(`/products/${product.slug}`);
  };

  return (
    <div className="p-8 max-w-7xl mx-auto pt-24 min-h-screen">
      <div className="flex flex-col md:flex-row items-center justify-between mb-8 gap-4">
        <h1 className="text-4xl font-display font-bold text-white uppercase tracking-widest">
          {searchParam ? `Search: ${searchParam}` : categoryParam ? `Category: ${categoryParam}` : 'VIEW PRODUCTS'}
        </h1>
        
        {/* Results count */}
        {!isLoading && data?.results && (
          <div className="text-sm text-gray-400 font-bold tracking-widest uppercase">
            {data.count} Results
          </div>
        )}
      </div>
      
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-6">
          {[1,2,3,4,5,6,7,8].map(i => (
            <div key={i} className="animate-pulse bg-white/5 rounded-xl h-80 border border-white/10"></div>
          ))}
        </div>
      ) : data?.results?.length === 0 ? (
        <div className="text-center py-20 text-gray-400 font-light text-xl">
          No products found matching your criteria.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-6">
          {data?.results?.map((product, i) => (
            <motion.div key={product.id} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}>
              <Link to={`/products/${product.slug}`}>
                <GlassCard className="h-full flex flex-col hover:border-white/30 transition-colors group cursor-pointer overflow-hidden p-4">
                  <div className="aspect-square bg-gray-900 mb-4 rounded-lg overflow-hidden relative">
                      <img src={product.thumbnail_url || 'https://via.placeholder.com/400?text=No+Image'} alt={product.name} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
                      <button 
                        onClick={(e) => handleToggleWishlist(e, product)}
                        className={`absolute top-2 right-2 p-2 rounded-full transition-colors z-10 ${wishlistProductIds.has(product.id) ? 'bg-red-500/90 text-white' : 'bg-black/50 text-white hover:bg-black/70'}`}
                      >
                        <Heart size={16} className={wishlistProductIds.has(product.id) ? 'fill-current' : ''} />
                      </button>
                  </div>
                  <h3 className="text-lg font-bold text-white truncate">{product.name}</h3>
                  <p className="text-gray-400 mb-2 truncate text-sm flex-grow">{product.description}</p>
                  <div className="text-xl font-bold text-white mb-4">{formatINR(product.base_price)}</div>
                  <div className="flex gap-2">
                    <button onClick={(e) => handleAddToCart(e, product)} className="flex-1 py-2 bg-white/10 hover:bg-white/20 text-white rounded transition-colors text-[10px] font-bold tracking-widest uppercase flex items-center justify-center gap-2">
                      <ShoppingCart size={14} /> Add
                    </button>
                    <button onClick={(e) => handleBuyNow(e, product)} className="flex-1 py-2 bg-white text-black hover:bg-gray-200 rounded transition-colors text-[10px] font-bold tracking-widest uppercase flex items-center justify-center gap-2">
                      <CreditCard size={14} /> Buy Now
                    </button>
                  </div>
                </GlassCard>
              </Link>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
