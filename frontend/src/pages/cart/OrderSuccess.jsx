import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { CheckCircle, Package, Truck, Calendar } from 'lucide-react';
import GlassCard from '../../components/ui/GlassCard';
import Button from '../../components/ui/Button';
import { motion } from 'framer-motion';

export default function OrderSuccess() {
  const navigate = useNavigate();
  const location = useLocation();

  // Optionally read state passed from Checkout
  const orderId = location.state?.orderId || `ORD-${Math.floor(100000 + Math.random() * 900000)}`;

  const expectedDelivery = new Date();
  expectedDelivery.setDate(expectedDelivery.getDate() + 5);

  return (
    <div className="p-8 max-w-3xl mx-auto pt-32 min-h-screen text-center">
      <motion.div
        initial={{ opacity: 0, scale: 0.9, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ duration: 0.5, ease: 'easeOut' }}
      >
        <GlassCard className="p-12 relative overflow-hidden">
          {/* Decorative background glow */}
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-64 h-64 bg-green-500/10 rounded-full blur-3xl -z-10"></div>

          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.2, type: 'spring', stiffness: 200 }}
            className="w-24 h-24 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-6"
          >
            <CheckCircle className="text-green-500 w-12 h-12" />
          </motion.div>

          <h1 className="text-4xl font-display font-bold text-white mb-2 uppercase tracking-widest">
            Payment Successful
          </h1>
          <h2 className="text-2xl font-bold text-gray-300 mb-8 uppercase tracking-widest">
            Order Confirmed
          </h2>

          <div className="bg-black/50 border border-white/10 rounded-lg p-6 mb-8 text-left grid gap-6 md:grid-cols-2">
            <div>
              <div className="text-xs text-gray-500 uppercase tracking-widest mb-1">Order ID</div>
              <div className="text-white font-bold font-mono">{orderId}</div>
            </div>
            <div>
              <div className="text-xs text-gray-500 uppercase tracking-widest mb-1 flex items-center gap-2">
                <Calendar size={14} /> Expected Delivery
              </div>
              <div className="text-green-400 font-bold">
                {expectedDelivery.toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' })}
              </div>
            </div>
          </div>

          <p className="text-gray-400 mb-8 max-w-lg mx-auto">
            Thank you for your purchase. We have sent a confirmation email with your order summary to your registered email address.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Button variant="primary" onClick={() => navigate('/dashboard/orders')} className="w-full sm:w-auto px-8 py-3">
              VIEW ORDERS
            </Button>
            <Button variant="outline" onClick={() => navigate('/products')} className="w-full sm:w-auto px-8 py-3">
              CONTINUE SHOPPING
            </Button>
          </div>
        </GlassCard>
      </motion.div>
    </div>
  );
}
