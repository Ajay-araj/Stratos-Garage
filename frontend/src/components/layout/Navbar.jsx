import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ShoppingCart, User, LogOut, ChevronDown, Search } from 'lucide-react';
import useAuthStore from '../../store/useAuthStore';
import useCartStore from '../../store/useCartStore';
import api from '../../services/api';

export default function Navbar() {
  const { user, logout } = useAuthStore();
  const itemCount = useCartStore(state => state.itemCount);
  const { setItemCount } = useCartStore();
  const navigate = useNavigate();
  const [categories, setCategories] = useState([]);
  const [isCategoryOpen, setIsCategoryOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    const fetchCategories = async () => {
      try {
        const res = await api.get('/products/categories/flat/');
        setCategories(res.data);
      } catch (err) {
        console.error(err);
      }
    };
    fetchCategories();
  }, []);

  // Sync cart badge count from backend whenever user changes
  useEffect(() => {
    if (user) {
      api.get('orders/cart/')
        .then(res => setItemCount(res.data.item_count ?? 0))
        .catch(() => {});
    } else {
      setItemCount(0);
    }
  }, [user, setItemCount]);

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const handleSearch = (e) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      navigate(`/products?q=${encodeURIComponent(searchQuery.trim())}`);
      setSearchQuery('');
    }
  };

  return (
    <nav className="fixed top-0 w-full z-50 bg-black/80 backdrop-blur-md border-b border-white/10">
      <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between gap-4">
        <Link to="/" className="text-2xl font-display font-bold text-white tracking-widest flex-shrink-0">STRATOS GARAGE</Link>
        
        <div className="hidden md:flex gap-6 items-center text-xs font-bold tracking-widest text-gray-300 relative">
          <Link to="/products" className="hover:text-white transition-colors uppercase">VIEW PRODUCTS</Link>
          
          <div 
            className="relative"
            onMouseEnter={() => setIsCategoryOpen(true)}
            onMouseLeave={() => setIsCategoryOpen(false)}
          >
            <button className="hover:text-white transition-colors uppercase flex items-center gap-1 h-16">
              CATEGORIES <ChevronDown size={14} />
            </button>
            {isCategoryOpen && (
              <div className="absolute top-16 left-0 w-48 bg-black/90 border border-white/10 rounded-b-lg overflow-hidden py-2 shadow-2xl">
                {categories.map(cat => (
                  <Link 
                    key={cat.id} 
                    to={`/shop/${cat.slug}`}
                    className="block px-4 py-2 hover:bg-white/10 text-white uppercase"
                  >
                    {cat.name}
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>

        <form onSubmit={handleSearch} className="hidden md:flex relative flex-grow max-w-sm mx-4">
          <input 
            type="text" 
            placeholder="Search products..." 
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-white/5 border border-white/10 text-white px-4 py-1.5 pr-10 rounded-full outline-none focus:border-white/30 text-sm"
          />
          <button type="submit" className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white">
            <Search size={16} />
          </button>
        </form>

        <div className="flex gap-4 items-center text-gray-300">
          <Link to="/cart" className="hover:text-white transition-colors relative">
            <ShoppingCart size={20} />
            {itemCount > 0 && (
              <span className="absolute -top-2 -right-2 bg-white text-black text-xs font-bold w-4 h-4 rounded-full flex items-center justify-center">
                {itemCount > 99 ? '99+' : itemCount}
              </span>
            )}
          </Link>
          {user ? (
            <div className="flex items-center gap-4">
              {user.role === 'seller' && (
                <Link to="/seller" className="px-3 py-1 bg-white text-black text-[10px] font-bold tracking-widest uppercase hover:bg-gray-200 transition-colors rounded hidden lg:block">SELLER DASHBOARD</Link>
              )}
              <div className="relative group">
                <Link to="/dashboard" className="hover:text-white transition-colors h-16 flex items-center"><User size={20} /></Link>
                <div className="absolute right-0 top-16 w-48 bg-black/95 border border-white/10 rounded-b-lg overflow-hidden py-2 shadow-2xl opacity-0 group-hover:opacity-100 pointer-events-none group-hover:pointer-events-auto transition-opacity">
                  <div className="px-4 py-2 border-b border-white/10 mb-2">
                    <p className="text-white text-sm font-bold truncate">{user.first_name || user.username}</p>
                    <p className="text-gray-500 text-xs truncate">{user.email}</p>
                  </div>
                  <Link to="/dashboard" className="block px-4 py-2 text-xs hover:bg-white/10 text-white uppercase tracking-widest transition-colors">My Profile</Link>
                  <Link to="/orders" className="block px-4 py-2 text-xs hover:bg-white/10 text-white uppercase tracking-widest transition-colors">View Orders</Link>
                  <Link to="/dashboard/wishlist" className="block px-4 py-2 text-xs hover:bg-white/10 text-white uppercase tracking-widest transition-colors">Wishlist</Link>
                  <button onClick={handleLogout} className="w-full text-left px-4 py-2 mt-2 border-t border-white/10 text-xs hover:bg-white/10 text-red-500 uppercase tracking-widest transition-colors flex items-center justify-between">
                    Logout <LogOut size={14} />
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <Link to="/login" className="hover:text-white transition-colors text-sm font-bold tracking-widest">LOGIN</Link>
          )}
        </div>
      </div>
    </nav>
  );
}
