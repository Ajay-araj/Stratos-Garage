import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Package, Plus, Edit2, Trash2, Save, X, Archive } from 'lucide-react';
import GlassCard from '../../components/ui/GlassCard';
import Button from '../../components/ui/Button';
import api from '../../services/api';
import { formatINR } from '../../utils/currency';

export default function SellerDashboard() {
  const queryClient = useQueryClient();
  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState({ price: '', stock: '' });
  const [activeTab, setActiveTab] = useState('products');

  const { data: stats = { total_revenue: '0', products_sold: 0, active_products: 0, pending_orders: 0 }, refetch: refetchStats } = useQuery({
    queryKey: ['sellerStats'],
    queryFn: () => api.get('/sellers/dashboard/').then(res => res.data),
    refetchInterval: 5000 // Live updates every 5 seconds
  });

  const { data: products = [], isLoading: loadingProducts, refetch: refetchProducts } = useQuery({
    queryKey: ['sellerProducts'],
    queryFn: () => api.get('/sellers/dashboard/products/').then(res => res.data),
    enabled: activeTab === 'products',
  });

  const { data: orders = [], isLoading: loadingOrders, refetch: refetchOrders } = useQuery({
    queryKey: ['sellerOrders'],
    queryFn: () => api.get('/orders/seller/orders/').then(res => res.data),
    enabled: activeTab === 'orders',
    refetchInterval: 5000 // Live updates for orders too
  });

  const loading = activeTab === 'products' ? loadingProducts : loadingOrders;

  // Old fetch logic removed as react-query handles this now

  const handleArchive = async (slug) => {
    if (window.confirm('Are you sure you want to archive this product?')) {
      try {
        await api.post(`/products/${slug}/archive/`);
        queryClient.invalidateQueries(['sellerProducts']);
      } catch (err) {
        alert('Failed to archive product');
      }
    }
  };

  const handleDelete = async (slug) => {
    if (window.confirm('WARNING: This will permanently delete this product and all associated data. Are you absolutely sure?')) {
      try {
        await api.delete(`/products/${slug}/delete/`);
        queryClient.invalidateQueries(['sellerProducts']);
      } catch (err) {
        alert('Failed to delete product permanently');
      }
    }
  };

  const handleEdit = (product) => {
    setEditingId(product.id);
    setEditForm({ price: product.price, stock: product.stock });
  };

  const handleSave = async (product) => {
    try {
      if (product.variant_id) {
        await api.patch(`/products/variants/${product.variant_id}/`, { price: editForm.price });
        await api.patch(`/inventory/${product.variant_id}/`, { quantity_available: editForm.stock });
      }
      setEditingId(null);
      queryClient.invalidateQueries(['sellerProducts']);
    } catch (err) {
      alert('Failed to update product');
    }
  };

  const handleStatusUpdate = async (orderNumber, status) => {
    try {
      await api.patch(`/orders/seller/orders/${orderNumber}/status/`, { status });
      queryClient.invalidateQueries(['sellerOrders']);
      queryClient.invalidateQueries(['sellerStats']);
    } catch (err) {
      alert(err.response?.data?.error || 'Failed to update order status');
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto pt-24 min-h-screen">
      <h1 className="text-3xl font-display font-bold text-white mb-8 tracking-widest">SELLER DASHBOARD</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
        <GlassCard className="p-6">
           <h3 className="text-gray-400 text-sm tracking-widest mb-2 uppercase">Total Revenue</h3>
           <div className="text-3xl font-bold text-white">{formatINR(stats.total_revenue)}</div>
        </GlassCard>
        <GlassCard className="p-6">
           <h3 className="text-gray-400 text-sm tracking-widest mb-2 uppercase">Products Sold</h3>
           <div className="text-3xl font-bold text-white">{stats.products_sold}</div>
        </GlassCard>
        <GlassCard className="p-6">
           <h3 className="text-gray-400 text-sm tracking-widest mb-2 uppercase">Pending Orders</h3>
           <div className="text-3xl font-bold text-white">{stats.pending_orders}</div>
        </GlassCard>
      </div>

      <div className="flex items-center gap-6 mb-8 border-b border-white/10 pb-4">
        <button 
          onClick={() => setActiveTab('products')} 
          className={`text-xl font-display font-bold tracking-widest flex items-center gap-3 pb-4 -mb-[17px] border-b-2 transition-colors ${activeTab === 'products' ? 'text-white border-white' : 'text-gray-500 border-transparent hover:text-gray-300'}`}
        >
          <Package size={20} /> Your Products
        </button>
        <button 
          onClick={() => setActiveTab('orders')} 
          className={`text-xl font-display font-bold tracking-widest flex items-center gap-3 pb-4 -mb-[17px] border-b-2 transition-colors ${activeTab === 'orders' ? 'text-white border-white' : 'text-gray-500 border-transparent hover:text-gray-300'}`}
        >
          <Package size={20} /> Manage Orders
        </button>

        {activeTab === 'products' && (
          <div className="ml-auto">
            <Link to="/dashboard/add-product">
              <Button variant="primary" className="flex items-center gap-2 text-xs py-2">
                <Plus size={16} /> Add Product
              </Button>
            </Link>
          </div>
        )}
      </div>

      {loading ? (
        <div className="text-center text-gray-400 py-12">Loading...</div>
      ) : activeTab === 'products' ? (
        products.length === 0 ? (
          <GlassCard className="p-16 text-center flex flex-col items-center justify-center border-dashed">
            <Package size={48} className="text-gray-600 mb-4" />
            <p className="text-xl text-gray-400 mb-6 font-light">No products uploaded yet</p>
            <Link to="/dashboard/add-product">
              <Button variant="primary" className="flex items-center gap-2">
                <Plus size={18} /> Add Product
              </Button>
            </Link>
          </GlassCard>
        ) : (
        <div className="grid grid-cols-1 gap-4">
          {products.map(product => (
            <GlassCard key={product.id} className="p-4 flex flex-col md:flex-row items-center gap-6 group hover:border-white/30 transition-colors">
              <div className="w-full md:w-32 h-32 bg-gray-900 rounded overflow-hidden flex-shrink-0 relative">
                {product.image ? (
                  <img src={product.image} alt={product.name} className="w-full h-full object-cover" />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-xs text-gray-500">NO IMAGE</div>
                )}
                {!product.is_active && (
                  <div className="absolute inset-0 bg-black/70 flex items-center justify-center text-[10px] text-red-500 font-bold uppercase tracking-widest">Inactive</div>
                )}
              </div>
              
              <div className="flex-grow w-full">
                <div className="text-[10px] tracking-widest text-gray-500 uppercase mb-1">{product.category}</div>
                <h3 className="text-lg font-bold text-white mb-2">{product.name}</h3>
                
                {editingId === product.id ? (
                  <div className="flex flex-wrap gap-4 items-end">
                    <div className="space-y-1">
                      <label className="text-[10px] text-gray-400 uppercase tracking-widest">Price (INR)</label>
                      <input type="number" step="0.01" value={editForm.price} onChange={e => setEditForm({...editForm, price: e.target.value})} className="w-24 bg-black border border-white/20 text-white px-2 py-1 rounded text-sm outline-none" />
                    </div>
                    <div className="space-y-1">
                      <label className="text-[10px] text-gray-400 uppercase tracking-widest">Stock</label>
                      <input type="number" value={editForm.stock} onChange={e => setEditForm({...editForm, stock: e.target.value})} className="w-20 bg-black border border-white/20 text-white px-2 py-1 rounded text-sm outline-none" />
                    </div>
                    <div className="flex gap-2 pb-1">
                      <button onClick={() => handleSave(product)} className="text-green-500 hover:text-green-400"><Save size={18} /></button>
                      <button onClick={() => setEditingId(null)} className="text-gray-500 hover:text-white"><X size={18} /></button>
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-wrap gap-6 mt-2">
                    <div className="text-xl font-display text-white">{formatINR(product.price)}</div>
                    <div className="text-sm text-gray-400 flex items-center">Stock: <span className="text-white ml-2">{product.stock}</span></div>
                    <div className={`text-[10px] font-bold uppercase tracking-widest px-2 py-1 rounded self-center ${product.is_active ? 'bg-green-500/20 text-green-400 border border-green-500/30' : 'bg-red-500/20 text-red-400 border border-red-500/30'}`}>
                      {product.is_active ? 'Active' : 'Archived'}
                    </div>
                  </div>
                )}
              </div>

              <div className="flex gap-4 w-full md:w-auto mt-4 md:mt-0 justify-end md:justify-start">
                <button onClick={() => handleEdit(product)} className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded transition-colors" title="Edit Price/Stock">
                  <Edit2 size={18} />
                </button>
                {product.is_active && (
                  <button onClick={() => handleArchive(product.slug)} className="p-2 text-gray-400 hover:text-yellow-500 hover:bg-yellow-500/10 rounded transition-colors" title="Archive Product">
                    <Archive size={18} />
                  </button>
                )}
                <button onClick={() => handleDelete(product.slug)} className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-500/10 rounded transition-colors" title="Delete Permanently">
                  <Trash2 size={18} />
                </button>
              </div>
            </GlassCard>
          ))}
        </div>
        )
      ) : (
        // ORDERS TAB
        orders.length === 0 ? (
          <GlassCard className="p-16 text-center flex flex-col items-center justify-center border-dashed">
            <Package size={48} className="text-gray-600 mb-4" />
            <p className="text-xl text-gray-400 font-light">No orders received yet</p>
          </GlassCard>
        ) : (
          <div className="grid grid-cols-1 gap-6">
            {orders.map(order => (
              <GlassCard key={order.id} className="p-6">
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center border-b border-white/10 pb-4 mb-4 gap-4">
                  <div>
                    <div className="text-gray-300 font-mono text-lg">Order #{order.order_number}</div>
                    <div className="text-gray-500 text-sm mt-1">{new Date(order.created_at).toLocaleDateString()}</div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2 border border-white/20 px-3 py-1.5 rounded bg-black/50 text-white mr-2">
                      <span className="uppercase tracking-widest text-[10px] text-gray-400">Payment:</span>
                      <span className={`uppercase tracking-widest text-[10px] font-bold ${order.payment_status === 'completed' ? 'text-green-400' : order.payment_status === 'failed' ? 'text-red-400' : 'text-yellow-400'}`}>
                        {order.payment_status === 'completed' ? 'PAID' : order.payment_status}
                      </span>
                    </div>
                    <div className="text-right">
                      <div className="text-xs text-gray-400 uppercase tracking-widest mb-1">Update Status</div>
                      <select 
                        value={order.order_status} 
                        onChange={(e) => handleStatusUpdate(order.order_number, e.target.value)}
                        className="bg-black border border-white/20 text-white text-xs px-3 py-1.5 rounded outline-none cursor-pointer"
                      >
                        <option value="pending">Pending</option>
                        <option value="payment_confirmed">Payment Confirmed</option>
                        <option value="packed">Packed</option>
                        <option value="shipped">Shipped</option>
                        <option value="out_for_delivery">Out For Delivery</option>
                        <option value="delivered">Delivered</option>
                        <option value="cancelled">Cancelled</option>
                      </select>
                    </div>
                  </div>
                </div>

                <div className="space-y-4 mb-6">
                  {order.items.map(item => (
                    <div key={item.id} className="flex items-center gap-4 bg-white/5 p-3 rounded">
                      <div className="flex-1">
                        <div className="text-white font-bold">{item.product_name}</div>
                        <div className="text-xs text-gray-400">Qty: {item.quantity} | SKU: {item.variant_sku}</div>
                      </div>
                      <div className="text-white font-bold">{formatINR(item.subtotal)}</div>
                    </div>
                  ))}
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm bg-black/30 p-4 rounded-lg">
                  <div>
                    <div className="text-gray-400 uppercase tracking-widest text-[10px] mb-1">Shipping To</div>
                    <div className="text-white">{order.shipping_name} ({order.shipping_phone})</div>
                    <div className="text-gray-300">{order.shipping_address_line1}, {order.shipping_city}, {order.shipping_state} {order.shipping_pincode}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-gray-400 uppercase tracking-widest text-[10px] mb-1">Total Amount</div>
                    <div className="text-xl font-bold text-white">{formatINR(order.total_price)}</div>
                  </div>
                </div>
              </GlassCard>
            ))}
          </div>
        )
      )}
    </div>
  );
}
