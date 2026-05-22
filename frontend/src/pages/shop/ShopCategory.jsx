import React from 'react';
import { useParams, Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import api from '../../services/api';
import GlassCard from '../../components/ui/GlassCard';
import { motion } from 'framer-motion';
import { ShoppingCart, CreditCard, Heart, Search } from 'lucide-react';
import useAuthStore from '../../store/useAuthStore';
import { formatINR } from '../../utils/currency';

const DEFAULT_BANNER = '/images/categories/default-category-banner.jpg';

const CATEGORY_INFO = {
  'motorcycles': {
    title: 'Motorcycle',
    description: 'The flagship premium motorcycle.',
    bannerUrl: '/images/categories/motorcycles-banner.jpg',
    apiCategory: 'motorcycles',
    searchPlaceholder: 'Search motorcycles...'
  },
  'riding-gear': {
    title: 'Riding Gear',
    description: 'Premium helmets, jackets, and riding accessories.',
    bannerUrl: '/images/categories/riding-gear-banner.jpg',
    apiCategory: 'riding-gear',
    searchPlaceholder: 'Search riding gear...'
  },
  'performance-parts': {
    title: 'Performance Parts',
    description: 'High-end exhaust systems and upgrades.',
    bannerUrl: '/images/categories/performance-parts-banner.jpg',
    apiCategory: 'performance-parts',
    searchPlaceholder: 'Search performance parts...'
  },
  'racing-collection': {
    title: 'Racing Collection',
    description: 'Track-ready racing gear and accessories.',
    bannerUrl: '/images/categories/racing-collection-banner.jpg',
    apiCategory: 'racing-collection',
    searchPlaceholder: 'Search racing collection...'
  }
};

export default function ShopCategory() {
  const { categorySlug } = useParams();
  const formatSlugToTitle = (slug) => {
    if (!slug) return 'Shop';
    return slug.split('-').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
  };

  const info = CATEGORY_INFO[categorySlug] || {
    title: formatSlugToTitle(categorySlug),
    description: `Explore our premium collection of ${formatSlugToTitle(categorySlug).toLowerCase()}.`,
    bannerUrl: DEFAULT_BANNER,
    apiCategory: categorySlug,
    searchPlaceholder: `Search ${formatSlugToTitle(categorySlug).toLowerCase()}...`
  };

  const [searchParams, setSearchParams] = useSearchParams();
  const searchParam = searchParams.get('q') || '';
  
  const { data, isLoading } = useQuery({
    queryKey: ['products', searchParam, info.apiCategory],
    queryFn: () => api.get('products/', {
      params: {
        q: searchParam || undefined,
        category: info.apiCategory || undefined,
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
  
  const navigate = useNavigate();

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

  const handleSearch = (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const q = fd.get('q');
    if (q) {
      setSearchParams({ q });
    } else {
      setSearchParams({});
    }
  };

  return (
    <div className="min-h-screen pt-16">
      {/* Banner */}
      <div className="relative h-64 md:h-[400px] w-full overflow-hidden">
        <motion.img 
          key={info.bannerUrl}
          initial={{ scale: 1.1, opacity: 0 }}
          animate={{ scale: 1, opacity: 0.6 }}
          transition={{ duration: 1.5, ease: "easeOut" }}
          src={info.bannerUrl} 
          onError={(e) => {
            e.target.src = "/images/categories/default-category-banner.jpg";
          }}
          alt={info.title} 
          className="absolute inset-0 w-full h-full object-cover" 
        />
        <motion.div 
          key={`overlay-${info.bannerUrl}`}
          initial={{ opacity: 0 }} 
          animate={{ opacity: 1 }} 
          transition={{ duration: 1 }}
          className="absolute inset-0 bg-gradient-to-t from-stratos-graphite via-stratos-graphite/40 to-transparent" 
        />
        <div className="absolute inset-0 flex flex-col justify-center items-center text-center p-4">
          <motion.h1 
            key={`title-${info.title}`}
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="text-4xl md:text-6xl font-display font-bold text-white uppercase tracking-widest mb-4 drop-shadow-xl"
          >
            {info.title}
          </motion.h1>
          <motion.p 
            key={`desc-${info.description}`}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.4 }}
            className="text-gray-300 max-w-2xl text-sm md:text-lg font-light drop-shadow-md"
          >
            {info.description}
          </motion.p>
        </div>
      </div>

      <div className="p-8 max-w-7xl mx-auto">
        <div className="flex flex-col md:flex-row items-center justify-between mb-8 gap-4">
          <form onSubmit={handleSearch} className="w-full md:w-96 relative">
            <input 
              type="text" 
              name="q"
              defaultValue={searchParam}
              placeholder={info.searchPlaceholder || `Search in ${info.title.toLowerCase()}...`} 
              className="w-full bg-white/5 border border-white/10 rounded-full px-4 py-2 pl-10 text-white focus:outline-none focus:border-white/30 transition-colors"
            />
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
          </form>
          
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
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center py-32 bg-white/5 rounded-2xl border border-white/10 backdrop-blur-sm"
          >
            <h2 className="text-2xl font-display font-bold text-white uppercase tracking-widest mb-4">No products found in this category.</h2>
            <p className="text-gray-400 font-light text-lg">
              Check back later as we continuously add premium {info.title.toLowerCase()} to our collection.
            </p>
          </motion.div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-6">
            {data?.results?.map((product, i) => (
              <motion.div key={product.id} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}>
                <Link to={`/products/${product.slug}`}>
                  <GlassCard className="h-full flex flex-col hover:border-white/30 transition-colors group cursor-pointer overflow-hidden p-4">
                    <div className="aspect-square bg-gray-900 mb-4 rounded-lg overflow-hidden relative">
                        <img src={product.thumbnail_url || 'https://via.placeholder.com/400?text=No+Image'} alt={product.name} loading="lazy" className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
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
                      <button onClick={(e) => { e.preventDefault(); navigate(`/products/${product.slug}`); }} className="flex-1 py-2 bg-white/10 hover:bg-white/20 text-white rounded transition-colors text-[10px] font-bold tracking-widest uppercase flex items-center justify-center gap-2">
                        <ShoppingCart size={14} /> Add
                      </button>
                      <button onClick={(e) => { e.preventDefault(); navigate(`/products/${product.slug}`); }} className="flex-1 py-2 bg-white text-black hover:bg-gray-200 rounded transition-colors text-[10px] font-bold tracking-widest uppercase flex items-center justify-center gap-2">
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
    </div>
  );
}
