import React, { useState, useEffect, useRef } from 'react';
import QRCode from 'react-qr-code';
import { motion, AnimatePresence } from 'framer-motion';
import { X, CheckCircle, Smartphone, Loader2, ShieldCheck } from 'lucide-react';

const UPI_APPS = [
  { name: 'GPay',    color: '#4285F4', letter: 'G' },
  { name: 'PhonePe', color: '#5f259f', letter: 'P' },
  { name: 'Paytm',   color: '#00BAF2', letter: 'P' },
  { name: 'BHIM',    color: '#00836C', letter: 'B' },
];

const COUNTDOWN_SECONDS = 300; // 5 min expiry, typical UPI behaviour

export default function PaymentModal({ amount, orderId, onConfirm, onClose, isPlacing }) {
  const [phase, setPhase] = useState('qr');       // 'qr' | 'processing' | 'success'
  const [countdown, setCountdown] = useState(COUNTDOWN_SECONDS);
  const intervalRef = useRef(null);

  const qrPayload = `${window.location.origin}/scan-pay/${orderId}`;

  // Countdown clock
  useEffect(() => {
    if (phase !== 'qr') return;
    intervalRef.current = setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1) { clearInterval(intervalRef.current); return 0; }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(intervalRef.current);
  }, [phase]);

  const formatTime = (s) => `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;

  const handleSimulateSuccess = () => {
    clearInterval(intervalRef.current);
    setPhase('processing');
    // Simulate 2.5 s processing, then place order
    setTimeout(async () => {
      await onConfirm();
      setPhase('success');
    }, 2500);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ backdropFilter: 'blur(16px)', background: 'rgba(0,0,0,0.75)' }}
    >
      <AnimatePresence mode="wait">

        {/* QR Phase */}
        {phase === 'qr' && (
          <motion.div
            key="qr"
            initial={{ opacity: 0, scale: 0.92, y: 24 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.92 }}
            transition={{ duration: 0.3 }}
            className="relative w-full max-w-sm rounded-2xl overflow-hidden"
            style={{ background: 'linear-gradient(135deg, rgba(255,255,255,0.07) 0%, rgba(0,0,0,0.6) 100%)', border: '1px solid rgba(255,255,255,0.12)' }}
          >
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-white/10">
              <div>
                <div className="text-xs uppercase tracking-widest text-gray-400">Stratos Garage</div>
                <div className="text-2xl font-bold text-white font-display">₹{Number(amount).toLocaleString('en-IN')}</div>
              </div>
              <button
                onClick={onClose}
                className="text-gray-500 hover:text-white transition-colors p-1 rounded-full"
              >
                <X size={20} />
              </button>
            </div>

            {/* QR Body */}
            <div className="px-6 py-6 flex flex-col items-center gap-4">
              {/* Animated scan ring */}
              <div className="relative">
                <motion.div
                  className="absolute inset-0 rounded-xl"
                  style={{ border: '2px solid rgba(255,255,255,0.3)' }}
                  animate={{ opacity: [0.3, 1, 0.3] }}
                  transition={{ duration: 2, repeat: Infinity }}
                />
                <div
                  className="p-3 rounded-xl cursor-pointer"
                  style={{ background: '#fff' }}
                  onClick={handleSimulateSuccess}
                  title="Click to simulate scan & payment"
                >
                  <QRCode
                    value={qrPayload}
                    size={180}
                    bgColor="#ffffff"
                    fgColor="#000000"
                    level="M"
                  />
                </div>
              </div>

              <div className="text-center">
                <p className="text-white font-medium text-sm">Scan with any UPI app</p>
                <p className="text-gray-500 text-xs mt-1">stratosgarage@upi</p>
              </div>

              {/* UPI App shortcuts */}
              <div className="flex items-center gap-3">
                {UPI_APPS.map(app => (
                  <button
                    key={app.name}
                    onClick={handleSimulateSuccess}
                    title={`Pay with ${app.name}`}
                    className="flex flex-col items-center gap-1 group"
                  >
                    <div
                      className="w-10 h-10 rounded-full flex items-center justify-center text-white text-sm font-bold shadow-lg group-hover:scale-110 transition-transform"
                      style={{ background: app.color }}
                    >
                      {app.letter}
                    </div>
                    <span className="text-gray-500 text-xs">{app.name}</span>
                  </button>
                ))}
              </div>

              {/* Waiting indicator */}
              <div className="flex items-center gap-2 text-gray-400 text-xs">
                <motion.div
                  animate={{ opacity: [0.4, 1, 0.4] }}
                  transition={{ duration: 1.5, repeat: Infinity }}
                  className="w-2 h-2 rounded-full bg-yellow-400"
                />
                Waiting for payment...
              </div>

              {/* Countdown */}
              <div className={`text-xs font-mono font-bold px-3 py-1 rounded-full border ${countdown < 60 ? 'border-red-500/40 text-red-400 bg-red-500/10' : 'border-white/10 text-gray-400'}`}>
                Expires in {formatTime(countdown)}
              </div>

              {/* Order ID */}
              <div className="text-xs text-gray-600 font-mono">Ref: {orderId}</div>
            </div>

            {/* Footer hint */}
            <div className="px-6 py-3 border-t border-white/10 flex items-center justify-center gap-2 text-xs text-gray-600">
              <ShieldCheck size={12} className="text-green-600" />
              <span>Demo mode — click QR or any app to simulate payment</span>
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
              className="w-20 h-20 rounded-full flex items-center justify-center"
              style={{ border: '3px solid rgba(255,255,255,0.1)', borderTop: '3px solid #fff' }}
            />
            <div>
              <div className="text-2xl font-bold text-white mb-2">Processing Payment</div>
              <div className="text-gray-400">Verifying transaction securely...</div>
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
            {/* Ripple rings */}
            <div className="relative flex items-center justify-center">
              {[1, 2, 3].map(i => (
                <motion.div
                  key={i}
                  className="absolute rounded-full border border-green-500/30"
                  initial={{ width: 80, height: 80, opacity: 1 }}
                  animate={{ width: 80 + i * 50, height: 80 + i * 50, opacity: 0 }}
                  transition={{ duration: 1.5, delay: i * 0.3, repeat: Infinity }}
                />
              ))}
              <motion.div
                className="w-20 h-20 bg-green-500/20 rounded-full flex items-center justify-center"
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ type: 'spring', stiffness: 300 }}
              >
                <CheckCircle className="text-green-500 w-10 h-10" />
              </motion.div>
            </div>
            <div>
              <div className="text-3xl font-bold text-white mb-1">Payment Successful!</div>
              <div className="text-gray-400">Redirecting to your orders...</div>
            </div>
          </motion.div>
        )}

      </AnimatePresence>
    </div>
  );
}
