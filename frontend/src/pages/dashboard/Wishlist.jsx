import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import api from '../../services/api';
import { formatINR } from '../../utils/currency';
import GlassCard from '../../components/ui/GlassCard';

export default function Wishlist() {
  const { data: wishlist, isLoading } = useQuery({
    queryKey: ['wishlist'],
    queryFn: () => api.get('wishlist/').then(res => res.data)
  });

  return (
    <div className="p-8 max-w-7xl mx-auto pt-24 min-h-screen">
      <h1 className="text-3xl font-display font-bold text-white mb-8">MY WISHLIST</h1>
      {isLoading ? <div className="text-white">Loading...</div> : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {wishlist?.results?.map(item => (
            <Link to={`/products/${item.product.slug}`} key={item.id}>
              <GlassCard className="p-4 hover:border-white/30 transition-colors cursor-pointer">
                <div className="text-lg font-bold text-white">{item.product.name}</div>
                <div className="text-gray-400">{formatINR(item.product.base_price)}</div>
              </GlassCard>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
