import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import api from '../../services/api';
import { formatINR } from '../../utils/currency';
import GlassCard from '../../components/ui/GlassCard';
import Button from '../../components/ui/Button';
import { Package, Truck, CheckCircle, ChevronRight, XCircle, RotateCcw, X, FileText } from 'lucide-react';

export default function Orders() {
  const queryClient = useQueryClient();
  const { data: orders, isLoading } = useQuery({
    queryKey: ['orders'],
    queryFn: () => api.get('orders/').then(res => res.data)
  });

  const navigate = useNavigate();

  const getStatusIcon = (status) => {
    switch (status) {
      case 'shipped':
      case 'out_for_delivery': return <Truck size={18} className="text-yellow-500" />;
      case 'delivered': return <CheckCircle size={18} className="text-green-500" />;
      case 'cancelled': return <XCircle size={18} className="text-red-500" />;
      default: return <Package size={18} className="text-blue-500" />;
    }
  };

  const timelineSteps = [
    { key: 'payment_confirmed', label: 'Payment Confirmed' },
    { key: 'packed', label: 'Packed' },
    { key: 'shipped', label: 'Shipped' },
    { key: 'out_for_delivery', label: 'Out For Delivery' },
    { key: 'delivered', label: 'Delivered' }
  ];

  const getStepStatus = (orderStatus, stepKey) => {
    if (orderStatus === 'cancelled') return 'cancelled';
    const statusOrder = ['pending', 'payment_confirmed', 'packed', 'shipped', 'out_for_delivery', 'delivered'];
    const currentIndex = statusOrder.indexOf(orderStatus);
    const stepIndex = statusOrder.indexOf(stepKey);
    
    if (currentIndex >= stepIndex) return 'completed';
    return 'pending';
  };

  const cancelMutation = useMutation({
    mutationFn: (orderNumber) => api.post(`orders/${orderNumber}/cancel/`),
    onSuccess: () => {
      queryClient.invalidateQueries(['orders']);
      alert('Order cancelled successfully.');
    },
    onError: (err) => {
      alert(err.response?.data?.error || 'Failed to cancel order.');
    }
  });

  const handleReorder = (order) => {
    // Add all items back to cart
    // Since add-to-cart takes variant_id and quantity, we would need to map it
    // For simplicity, navigate to products or just show alert
    alert('Reorder functionality will be available soon.');
  };

  return (
    <div className="p-8 max-w-7xl mx-auto pt-24 min-h-screen">
      <h1 className="text-3xl font-display font-bold text-white mb-8 tracking-widest">ORDER HISTORY</h1>
      {isLoading ? (
        <div className="text-gray-400">Loading orders...</div>
      ) : orders?.length === 0 ? (
        <GlassCard className="p-12 text-center flex flex-col items-center justify-center">
          <Package size={48} className="text-gray-500 mb-4" />
          <h2 className="text-2xl font-bold text-white mb-2">No Orders Yet</h2>
          <p className="text-gray-400 mb-8 font-light">You haven't placed any orders.</p>
          <Button variant="primary" onClick={() => navigate('/products')} className="px-8 py-3">START SHOPPING</Button>
        </GlassCard>
      ) : (
        <div className="space-y-6">
          {orders?.map(order => (
            <GlassCard key={order.id} className="p-6">
              <div className="flex flex-col md:flex-row justify-between items-start md:items-center border-b border-white/10 pb-4 mb-4 gap-4">
                <div>
                  <div className="text-gray-300 font-mono text-lg">Order #{order.order_number}</div>
                  <div className="text-gray-500 text-sm mt-1">{new Date(order.created_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' })}</div>
                </div>
                <div className="flex flex-col items-end gap-2">
                  <div className="flex items-center gap-2 border border-white/20 px-3 py-1.5 rounded bg-black/50 text-white">
                    <span className="uppercase tracking-widest text-[10px] text-gray-400">Payment:</span>
                    <span className={`uppercase tracking-widest text-[10px] font-bold ${order.payment_status === 'completed' ? 'text-green-400' : order.payment_status === 'failed' ? 'text-red-400' : 'text-yellow-400'}`}>
                      {order.payment_status === 'completed' ? 'PAID' : order.payment_status}
                    </span>
                  </div>
                  <div className={`flex items-center gap-2 border px-3 py-1.5 rounded bg-black/50 ${order.order_status === 'cancelled' ? 'border-red-500/50 text-red-400' : 'border-white/20 text-white'}`}>
                    {getStatusIcon(order.order_status)}
                    <span className="uppercase tracking-widest text-xs font-bold">{order.order_status.replace(/_/g, ' ')}</span>
                  </div>
                  {order.expected_delivery && order.order_status !== 'delivered' && order.order_status !== 'cancelled' && (
                    <div className="text-xs text-blue-400 tracking-wider">
                      Expected Delivery: {new Date(order.expected_delivery).toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' })}
                    </div>
                  )}
                </div>
              </div>

              {order.order_status !== 'cancelled' && (
                <div className="my-8 px-4">
                  <div className="relative flex justify-between items-center max-w-3xl mx-auto">
                    <div className="absolute left-0 top-1/2 -translate-y-1/2 w-full h-1 bg-white/10 rounded-full z-0"></div>
                    <div 
                      className="absolute left-0 top-1/2 -translate-y-1/2 h-1 bg-green-500 rounded-full z-0 transition-all duration-500"
                      style={{
                        width: (() => {
                          const statusOrder = ['pending', 'payment_confirmed', 'packed', 'shipped', 'out_for_delivery', 'delivered'];
                          let idx = statusOrder.indexOf(order.order_status);
                          if (idx <= 1) return '0%';
                          if (idx === 2) return '25%';
                          if (idx === 3) return '50%';
                          if (idx === 4) return '75%';
                          if (idx === 5) return '100%';
                          return '0%';
                        })()
                      }}
                    ></div>
                    
                    {timelineSteps.map((step, idx) => {
                      const status = getStepStatus(order.order_status, step.key);
                      return (
                        <div key={step.key} className="relative z-10 flex flex-col items-center gap-2">
                          <div className={`w-4 h-4 rounded-full border-2 ${status === 'completed' ? 'bg-green-500 border-green-500' : 'bg-black border-white/30'}`}></div>
                          <span className={`text-[10px] uppercase tracking-widest font-bold hidden sm:block ${status === 'completed' ? 'text-white' : 'text-gray-500'}`}>{step.label}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              <div className="space-y-4">
                {order.items.map(item => (
                  <div key={item.id} className="flex items-center gap-4">
                    <div className="w-16 h-16 bg-gray-900 rounded overflow-hidden flex-shrink-0">
                       <img src={item.product_image || 'https://via.placeholder.com/100'} alt={item.product_name} className="w-full h-full object-cover" />
                    </div>
                    <div className="flex-1">
                      <div className="text-white font-bold">{item.product_name}</div>
                      <div className="text-xs text-gray-400 mt-1">{item.variant_description}</div>
                      <div className="text-sm text-gray-400 mt-1">Qty: {item.quantity}</div>
                    </div>
                    <div className="text-white font-bold">{formatINR(item.subtotal)}</div>
                  </div>
                ))}
              </div>

              <div className="flex flex-col sm:flex-row justify-between items-center mt-6 pt-4 border-t border-white/10 gap-4">
                <div className="flex items-center gap-3 w-full sm:w-auto">
                  {(order.order_status === 'pending' || order.order_status === 'payment_confirmed') && (
                    <Button variant="outline" className="border-red-500/50 text-red-400 hover:bg-red-500/10 text-xs px-3 py-1.5 flex items-center gap-2" onClick={() => {
                      if (window.confirm('Are you sure you want to cancel this order?')) {
                        cancelMutation.mutate(order.order_number);
                      }
                    }}>
                      <X size={14} /> Cancel Order
                    </Button>
                  )}
                  <Button variant="outline" className="border-white/20 text-gray-300 hover:bg-white/10 text-xs px-3 py-1.5 flex items-center gap-2" onClick={() => handleReorder(order)}>
                    <RotateCcw size={14} /> Reorder
                  </Button>
                  <Button variant="outline" className="border-white/20 text-gray-300 hover:bg-white/10 text-xs px-3 py-1.5 flex items-center gap-2" onClick={async () => {
                    if (order.payment_status !== 'completed') {
                      alert('Invoice is only available for paid orders.');
                      return;
                    }
                    try {
                      const response = await api.get(`orders/${order.order_number}/invoice/`, { responseType: 'blob' });
                      const url = window.URL.createObjectURL(new Blob([response.data]));
                      const link = document.createElement('a');
                      link.href = url;
                      link.setAttribute('download', `Invoice_${order.order_number}.pdf`);
                      document.body.appendChild(link);
                      link.click();
                      link.parentNode.removeChild(link);
                    } catch (err) {
                      alert('Failed to download invoice.');
                    }
                  }}>
                    <FileText size={14} /> Invoice
                  </Button>
                </div>
                <div className="flex items-center gap-3 w-full sm:w-auto justify-between sm:justify-end">
                  <div className="text-sm text-gray-400 uppercase tracking-widest">Total Amount</div>
                  <div className="text-2xl font-bold text-white">{formatINR(order.total_price)}</div>
                </div>
              </div>
            </GlassCard>
          ))}
        </div>
      )}
    </div>
  );
}
