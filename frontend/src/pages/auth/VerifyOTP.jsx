import React, { useState, useRef, useEffect } from 'react';
import { useNavigate, useLocation, Navigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import api from '../../services/api';
import Button from '../../components/ui/Button';
import GlassCard from '../../components/ui/GlassCard';
import { motion } from 'framer-motion';

function parseError(data) {
  if (!data) return 'Verification failed. Please try again.';
  if (typeof data.message === 'string') return data.message;
  if (typeof data.error === 'string') return data.error;
  if (typeof data === 'object') {
    const first = Object.values(data)[0];
    if (Array.isArray(first)) return first[0];
    if (typeof first === 'string') return first;
  }
  return 'Verification failed. Please try again.';
}

export default function VerifyOTP() {
  const location = useLocation();
  const navigate = useNavigate();
  const email = location.state?.email || '';
  const successMsg = location.state?.message || '';

  // 6 individual digit inputs
  const [digits, setDigits] = useState(['', '', '', '', '', '']);
  const inputRefs = useRef([]);

  const code = digits.join('');

  const verifyMutation = useMutation({
    mutationFn: (data) => api.post('users/auth/verify-otp/', data),
    onSuccess: (response) => {
      const token = response.data.token;
      navigate('/create-password', { state: { token, email } });
    },
    onError: (error) => {
      console.error('OTP verify error:', error.response?.status, error.response?.data);
    },
  });

  const resendMutation = useMutation({
    mutationFn: () => api.post('users/auth/resend-otp/', { email }),
    onSuccess: () => {
      setDigits(['', '', '', '', '', '']);
      inputRefs.current[0]?.focus();
    },
  });

  // Auto-submit when all 6 digits filled
  useEffect(() => {
    if (code.length === 6 && digits.every((d) => d !== '')) {
      verifyMutation.mutate({ email, code });
    }
  }, [code]);

  const handleDigitChange = (index, value) => {
    const v = value.replace(/\D/g, '').slice(-1); // digits only, 1 char
    const next = [...digits];
    next[index] = v;
    setDigits(next);
    if (v && index < 5) inputRefs.current[index + 1]?.focus();
  };

  const handleKeyDown = (index, e) => {
    if (e.key === 'Backspace' && !digits[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  const handlePaste = (e) => {
    const text = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
    if (text.length > 0) {
      const next = text.split('').concat(Array(6).fill('')).slice(0, 6);
      setDigits(next);
      const focusIdx = Math.min(text.length, 5);
      inputRefs.current[focusIdx]?.focus();
    }
    e.preventDefault();
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (code.length !== 6) return;
    verifyMutation.mutate({ email, code });
  };

  if (!email) {
    return <Navigate to="/register" replace />;
  }

  const errorMessage = verifyMutation.isError ? parseError(verifyMutation.error?.response?.data) : '';

  return (
    <div className="min-h-screen flex items-center justify-center bg-black px-4 pt-16">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="w-full max-w-md"
      >
        <GlassCard className="p-8 border border-white/10">
          <h2 className="text-3xl font-display font-bold text-white mb-2 text-center tracking-widest">
            VERIFY EMAIL
          </h2>
          <p className="text-gray-500 text-center text-xs tracking-widest mb-2">
            STEP 2 OF 3 — EMAIL VERIFICATION
          </p>
          <p className="text-gray-400 text-center text-sm mb-4">
            We sent a 6-digit code to{' '}
            <span className="text-white font-medium">{email}</span>
          </p>

          {successMsg && (
            <div className="bg-green-500/10 border border-green-500/30 text-green-400 text-xs rounded px-4 py-2 text-center mb-4 tracking-wide">
              {successMsg}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* 6-box OTP input */}
            <div className="flex justify-center gap-3" onPaste={handlePaste}>
              {digits.map((digit, i) => (
                <input
                  key={i}
                  ref={(el) => (inputRefs.current[i] = el)}
                  type="text"
                  inputMode="numeric"
                  maxLength={1}
                  value={digit}
                  onChange={(e) => handleDigitChange(i, e.target.value)}
                  onKeyDown={(e) => handleKeyDown(i, e)}
                  className={`w-12 h-14 text-center text-2xl font-mono font-bold bg-white/5 border rounded-lg text-white outline-none transition-all
                    ${digit ? 'border-white/60' : 'border-white/20'}
                    focus:border-white focus:bg-white/10`}
                />
              ))}
            </div>

            {errorMessage && (
              <div className="bg-red-500/10 border border-red-500/40 text-red-400 text-sm rounded px-4 py-3 text-center">
                {errorMessage}
              </div>
            )}

            <Button
              type="submit"
              variant="primary"
              className="w-full py-3"
              isLoading={verifyMutation.isPending}
              disabled={code.length !== 6}
            >
              VERIFY CODE
            </Button>
          </form>

          <div className="mt-8 text-center border-t border-white/10 pt-6 space-y-2">
            <button
              type="button"
              onClick={() => resendMutation.mutate()}
              disabled={resendMutation.isPending}
              className="text-gray-400 hover:text-white transition-colors text-xs tracking-widest uppercase"
            >
              {resendMutation.isPending ? 'SENDING...' : 'RESEND CODE'}
            </button>
            {resendMutation.isSuccess && (
              <p className="text-green-400 text-xs">New code sent to your email.</p>
            )}
            {resendMutation.isError && (
              <p className="text-red-400 text-xs">
                {parseError(resendMutation.error?.response?.data)}
              </p>
            )}
          </div>
        </GlassCard>
      </motion.div>
    </div>
  );
}
