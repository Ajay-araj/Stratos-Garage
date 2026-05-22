import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../../services/api';
import GlassCard from '../../components/ui/GlassCard';
import { CheckCircle, Smartphone, ShieldCheck } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function ScanPay() {
  const { orderId } = useParams();
  const navigate = useNavigate();
  const [phase, setPhase] = useState('scanning'); // 'scanning' | 'processing' | 'success' | 'error'

  useEffect(() => {
    // 1. Simulate "Waiting for scan..." / identifying order
    const scanTimeout = setTimeout(() => {
      setPhase('processing');

      // 2. Visually simulate processing, then show success.
      // (The actual backend DB update, cart clearing, and emails are triggered 
      // by the desktop browser when the simulated flow completes there).
      setTimeout(() => {
        setPhase('success');
        // 3. Redirect to success page on the mobile device
        setTimeout(() => {
          navigate('/orders/success', { state: { orderId } });
        }, 2500);
      }, 2000);
    }, 1500);

    return () => clearTimeout(scanTimeout);
  }, [orderId, navigate]);

  return (
    <div className="min-h-screen bg-black flex items-center justify-center p-4">
      <GlassCard className="w-full max-w-sm p-8 text-center relative overflow-hidden">
        {/* Animated Background */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-64 h-64 bg-white/5 rounded-full blur-3xl -z-10"></div>

        <AnimatePresence mode="wait">
          {/* Scanning Phase */}
          {phase === 'scanning' && (
            <motion.div
              key="scanning"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="flex flex-col items-center gap-6"
            >
              <div className="relative">
                <Smartphone size={48} className="text-gray-400" />
                <motion.div
                  className="absolute inset-0 border-2 border-white rounded-lg"
                  animate={{ opacity: [0, 1, 0], scale: [1, 1.2, 1] }}
                  transition={{ duration: 1.5, repeat: Infinity }}
                />
              </div>
              <div>
                <h2 className="text-xl font-bold text-white mb-2">QR Code Scanned</h2>
                <p className="text-gray-400 text-sm">Identifying secure payment link...</p>
              </div>
            </motion.div>
          )}

          {/* Processing Phase */}
          {phase === 'processing' && (
            <motion.div
              key="processing"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
              className="flex flex-col items-center gap-6 text-center"
            >
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                className="w-16 h-16 rounded-full flex items-center justify-center"
                style={{ border: '3px solid rgba(255,255,255,0.1)', borderTop: '3px solid #fff' }}
              />
              <div>
                <h2 className="text-xl font-bold text-white mb-2">Processing Payment</h2>
                <p className="text-gray-400 text-sm flex items-center justify-center gap-2">
                  <ShieldCheck size={14} className="text-green-500" />
                  Verifying transaction internally
                </p>
                <div className="text-xs font-mono text-gray-500 mt-4 bg-black/40 py-1 px-3 rounded-full border border-white/10">
                  Ref: {orderId}
                </div>
              </div>
            </motion.div>
          )}

          {/* Success Phase */}
          {phase === 'success' && (
            <motion.div
              key="success"
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
              transition={{ type: 'spring', stiffness: 200, damping: 15 }}
              className="flex flex-col items-center gap-6 text-center"
            >
              <div className="relative flex items-center justify-center">
                {[1, 2, 3].map(i => (
                  <motion.div
                    key={i}
                    className="absolute rounded-full border border-green-500/30"
                    initial={{ width: 64, height: 64, opacity: 1 }}
                    animate={{ width: 64 + i * 40, height: 64 + i * 40, opacity: 0 }}
                    transition={{ duration: 1.5, delay: i * 0.3, repeat: Infinity }}
                  />
                ))}
                <motion.div
                  className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center relative z-10"
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ type: 'spring', stiffness: 300 }}
                >
                  <CheckCircle className="text-green-500 w-8 h-8" />
                </motion.div>
              </div>
              <div>
                <h2 className="text-2xl font-bold text-white mb-2">Payment Successful!</h2>
                <p className="text-gray-400 text-sm mb-1">Order marked as PAID</p>
                <p className="text-gray-500 text-xs">Redirecting to order confirmation...</p>
              </div>
            </motion.div>
          )}

          {/* Error Phase */}
          {phase === 'error' && (
            <motion.div
              key="error"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="flex flex-col items-center gap-4 text-center"
            >
              <div className="w-16 h-16 bg-red-500/20 rounded-full flex items-center justify-center text-red-500 text-2xl font-bold">!</div>
              <h2 className="text-xl font-bold text-white mb-2">Payment Failed</h2>
              <p className="text-red-400 text-sm">Could not verify order {orderId}</p>
            </motion.div>
          )}
        </AnimatePresence>
      </GlassCard>
    </div>
  );
}
