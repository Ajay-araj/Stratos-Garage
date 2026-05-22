import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Package, Plus, MapPin, Save } from 'lucide-react';
import useAuthStore from '../../store/useAuthStore';
import GlassCard from '../../components/ui/GlassCard';
import Button from '../../components/ui/Button';
import api from '../../services/api';
import { formatINR } from '../../utils/currency';

export default function Profile() {
  const user = useAuthStore(state => state.user);
  const setUser = useAuthStore(state => state.setUser);
  
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [addresses, setAddresses] = useState([]);
  const [addressForm, setAddressForm] = useState({
    id: null,
    full_name: user?.first_name ? `${user.first_name} ${user.last_name}` : '',
    phone: user?.phone || '',
    address_line1: '',
    address_line2: '',
    city: '',
    state: '',
    pincode: '',
    country: 'India',
  });
  const [savingAddress, setSavingAddress] = useState(false);

  useEffect(() => {
    const fetchAddresses = async () => {
      try {
        const response = await api.get('/users/addresses/');
        setAddresses(response.data);
        if (response.data.length > 0) {
          const defaultAddr = response.data.find(a => a.is_default) || response.data[0];
          setAddressForm({
            id: defaultAddr.id,
            full_name: defaultAddr.full_name,
            phone: defaultAddr.phone,
            address_line1: defaultAddr.address_line1,
            address_line2: defaultAddr.address_line2,
            city: defaultAddr.city,
            state: defaultAddr.state,
            pincode: defaultAddr.pincode,
            country: defaultAddr.country,
          });
        }
      } catch (err) {
        console.error('Failed to load addresses');
      }
    };
    fetchAddresses();

    if (user?.role === 'seller') {
      const fetchProducts = async () => {
        try {
          const response = await api.get('/sellers/dashboard/products/');
          setProducts(response.data);
        } catch (err) {
          setError('Failed to load recent products.');
        } finally {
          setLoading(false);
        }
      };
      fetchProducts();
    } else {
      setLoading(false);
    }
  }, [user]);

  const handleAddressSubmit = async (e) => {
    e.preventDefault();
    setSavingAddress(true);
    try {
      if (addressForm.id) {
        await api.patch(`/users/addresses/${addressForm.id}/`, addressForm);
      } else {
        const res = await api.post('/users/addresses/', { ...addressForm, is_default: true });
        setAddressForm({...addressForm, id: res.data.id});
      }
      alert('Address saved successfully');
    } catch (err) {
      alert('Failed to save address');
    } finally {
      setSavingAddress(false);
    }
  };

  return (
    <div className="p-8 max-w-6xl mx-auto pt-24 min-h-screen">
      <h1 className="text-3xl font-display font-bold text-white mb-8 tracking-widest">MY DASHBOARD</h1>
      
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-1 space-y-6">
          <GlassCard className="p-8">
            <h2 className="text-xl font-bold text-white mb-4 border-b border-white/10 pb-2">Profile Information</h2>
            <div className="text-gray-300 space-y-4 text-sm tracking-wide mt-6">
              <p><span className="text-gray-500 block text-xs uppercase mb-1">Name</span> {user?.first_name} {user?.last_name}</p>
              <p><span className="text-gray-500 block text-xs uppercase mb-1">Email</span> {user?.email}</p>
              <p><span className="text-gray-500 block text-xs uppercase mb-1">Role</span> <span className="uppercase tracking-widest text-xs border border-white/20 px-2 py-1 rounded">{user?.role || 'CUSTOMER'}</span></p>
            </div>
            <div className="mt-6 pt-6 border-t border-white/10 flex flex-col gap-3">
              <Link to="/orders" className="w-full text-center py-2 px-4 bg-white/5 border border-white/10 text-white rounded text-xs uppercase tracking-widest font-bold hover:bg-white/10 transition-colors flex justify-center items-center gap-2">
                <Package size={14} /> View My Orders
              </Link>
            </div>
          </GlassCard>

          <GlassCard className="p-8">
            <h2 className="text-xl font-bold text-white mb-4 border-b border-white/10 pb-2 flex items-center gap-2">
              <MapPin size={20} /> Address Information
            </h2>
            <form onSubmit={handleAddressSubmit} className="space-y-4 mt-6">
              <div>
                <label className="text-[10px] text-gray-400 uppercase tracking-widest mb-1 block">Full Name</label>
                <input required type="text" value={addressForm.full_name} onChange={e => setAddressForm({...addressForm, full_name: e.target.value})} className="w-full bg-black border border-white/20 text-white px-3 py-2 rounded text-sm outline-none" placeholder="John Doe" />
              </div>
              <div>
                <label className="text-[10px] text-gray-400 uppercase tracking-widest mb-1 block">Phone Number</label>
                <input required type="text" value={addressForm.phone} onChange={e => setAddressForm({...addressForm, phone: e.target.value})} className="w-full bg-black border border-white/20 text-white px-3 py-2 rounded text-sm outline-none" placeholder="+1 234 567 8900" />
              </div>
              <div>
                <label className="text-[10px] text-gray-400 uppercase tracking-widest mb-1 block">Address Line 1</label>
                <input required type="text" value={addressForm.address_line1} onChange={e => setAddressForm({...addressForm, address_line1: e.target.value})} className="w-full bg-black border border-white/20 text-white px-3 py-2 rounded text-sm outline-none" placeholder="123 Main St" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-[10px] text-gray-400 uppercase tracking-widest mb-1 block">City</label>
                  <input required type="text" value={addressForm.city} onChange={e => setAddressForm({...addressForm, city: e.target.value})} className="w-full bg-black border border-white/20 text-white px-3 py-2 rounded text-sm outline-none" placeholder="City" />
                </div>
                <div>
                  <label className="text-[10px] text-gray-400 uppercase tracking-widest mb-1 block">State</label>
                  <input required type="text" value={addressForm.state} onChange={e => setAddressForm({...addressForm, state: e.target.value})} className="w-full bg-black border border-white/20 text-white px-3 py-2 rounded text-sm outline-none" placeholder="State" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-[10px] text-gray-400 uppercase tracking-widest mb-1 block">Postal Code (PIN)</label>
                  <input required type="text" value={addressForm.pincode} onChange={e => setAddressForm({...addressForm, pincode: e.target.value})} className="w-full bg-black border border-white/20 text-white px-3 py-2 rounded text-sm outline-none" placeholder="ZIP" />
                </div>
                <div>
                  <label className="text-[10px] text-gray-400 uppercase tracking-widest mb-1 block">Country</label>
                  <input required type="text" value={addressForm.country} onChange={e => setAddressForm({...addressForm, country: e.target.value})} className="w-full bg-black border border-white/20 text-white px-3 py-2 rounded text-sm outline-none" placeholder="Country" />
                </div>
              </div>
              <Button type="submit" variant="primary" className="w-full mt-4 flex items-center justify-center gap-2" disabled={savingAddress}>
                <Save size={16} /> {savingAddress ? 'Saving...' : 'Save Address'}
              </Button>
            </form>
          </GlassCard>
        </div>

        {user?.role === 'seller' && (
          <div className="lg:col-span-2 space-y-6">
            <div className="flex items-center justify-between border-b border-white/10 pb-4">
              <h2 className="text-2xl font-display font-bold text-white tracking-widest flex items-center gap-3">
                <Package size={24} className="text-gray-400" />
                Recently Added Products
              </h2>
              <Link to="/dashboard/add-product" className="px-4 py-2 bg-white text-black text-xs font-bold tracking-widest uppercase hover:bg-gray-200 transition-colors rounded flex items-center gap-2">
                <Plus size={16} /> Add Product
              </Link>
            </div>

            {loading ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {[1, 2, 3, 4].map(i => (
                  <div key={i} className="animate-pulse bg-white/5 rounded-xl h-48 border border-white/10" />
                ))}
              </div>
            ) : error ? (
              <div className="bg-red-900/50 border border-red-500/50 text-red-200 p-4 rounded-lg">{error}</div>
            ) : products.length === 0 ? (
              <GlassCard className="p-12 text-center flex flex-col items-center justify-center">
                <Package size={48} className="text-gray-500 mb-4" />
                <p className="text-gray-400 mb-6 text-lg font-light">No products added yet.</p>
                <Link to="/dashboard/add-product" className="px-6 py-3 bg-white text-black text-sm font-bold tracking-widest uppercase hover:bg-gray-200 transition-colors rounded flex items-center gap-2">
                  <Plus size={18} /> Add Product
                </Link>
              </GlassCard>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {products.map((product, idx) => (
                  <motion.div 
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: idx * 0.1 }}
                    key={product.id}
                  >
                    <GlassCard className="overflow-hidden flex flex-col h-full group hover:border-white/30 transition-colors">
                      <div className="relative h-48 overflow-hidden bg-black/50">
                        {product.image ? (
                          <img src={product.image} alt={product.name} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center text-gray-600">No Image</div>
                        )}
                        <div className="absolute top-3 right-3 flex flex-col gap-2">
                          <span className={`px-2 py-1 text-[10px] font-bold tracking-widest uppercase rounded ${product.is_active ? 'bg-green-500/20 text-green-300 border border-green-500/30' : 'bg-red-500/20 text-red-300 border border-red-500/30'}`}>
                            {product.is_active ? 'Active' : 'Inactive'}
                          </span>
                          <span className="px-2 py-1 bg-black/80 backdrop-blur border border-white/20 text-white text-[10px] font-bold tracking-widest uppercase rounded">
                            Stock: {product.stock}
                          </span>
                        </div>
                      </div>
                      <div className="p-4 flex flex-col flex-grow">
                        <div className="text-[10px] tracking-widest text-gray-500 uppercase mb-1">{product.category}</div>
                        <h3 className="text-white font-bold mb-2 line-clamp-1">{product.name}</h3>
                        <div className="mt-auto pt-4 flex items-center justify-between">
                          <span className="text-lg font-display text-white">{formatINR(product.price)}</span>
                          <span className="text-[10px] text-gray-500 tracking-wider">ADDED {product.created_at}</span>
                        </div>
                      </div>
                    </GlassCard>
                  </motion.div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
