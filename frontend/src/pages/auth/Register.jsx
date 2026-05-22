import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import api from '../../services/api';
import Button from '../../components/ui/Button';
import Input from '../../components/ui/Input';
import GlassCard from '../../components/ui/GlassCard';
import { motion } from 'framer-motion';

// Extracts the first human-readable error string from any DRF error shape
function parseError(data) {
  if (!data) return 'Registration failed. Please try again.';
  // Standardised envelope: { message, errors }
  if (typeof data.message === 'string') return data.message;
  // DRF field errors: { email: ["already exists"], first_name: [...] }
  if (typeof data === 'object') {
    const first = Object.values(data)[0];
    if (Array.isArray(first)) return first[0];
    if (typeof first === 'string') return first;
  }
  return 'Registration failed. Please try again.';
}

export default function Register() {
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    role: 'buyer',
  });
  const [errorMsg, setErrorMsg] = useState('');
  const navigate = useNavigate();

  const set = (field) => (e) => setFormData((prev) => ({ ...prev, [field]: e.target.value }));

  const registerMutation = useMutation({
    mutationFn: (data) => api.post('users/auth/register/', data),
    onSuccess: (response) => {
      const resent = response.data?.resent;
      navigate('/verify-otp', {
        state: {
          email: formData.email,
          message: resent
            ? 'A new OTP has been resent to your email.'
            : 'OTP sent to your email. Please verify to continue.',
        },
      });
    },
    onError: (error) => {
      console.error('Register error:', error.response?.status, error.response?.data);
      setErrorMsg(parseError(error.response?.data));
    },
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    setErrorMsg('');
    // Only send non-empty phone so backend optional field stays clean
    const payload = {
      first_name: formData.first_name.trim(),
      last_name: formData.last_name.trim(),
      email: formData.email.trim(),
      role: formData.role,
    };
    if (formData.phone.trim()) payload.phone = formData.phone.trim();
    registerMutation.mutate(payload);
  };

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
            CREATE ACCOUNT
          </h2>
          <p className="text-gray-500 text-center text-xs tracking-widest mb-8">
            STEP 1 OF 3 — ACCOUNT DETAILS
          </p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <Input
                label="First Name"
                value={formData.first_name}
                onChange={set('first_name')}
                required
                autoComplete="given-name"
              />
              <Input
                label="Last Name"
                value={formData.last_name}
                onChange={set('last_name')}
                required
                autoComplete="family-name"
              />
            </div>

            <Input
              label="Email Address"
              type="email"
              value={formData.email}
              onChange={set('email')}
              required
              autoComplete="email"
            />

            <Input
              label="Phone (optional)"
              type="tel"
              value={formData.phone}
              onChange={set('phone')}
              autoComplete="tel"
            />

            <div className="space-y-1">
              <label className="block text-xs text-gray-400 tracking-widest uppercase">Account Type</label>
              <div className="grid grid-cols-2 gap-3">
                {['buyer', 'seller'].map((r) => (
                  <button
                    key={r}
                    type="button"
                    onClick={() => setFormData((prev) => ({ ...prev, role: r }))}
                    className={`py-2.5 text-xs tracking-widest uppercase border transition-all rounded ${
                      formData.role === r
                        ? 'bg-white text-black border-white font-semibold'
                        : 'bg-transparent text-gray-400 border-white/20 hover:border-white/50'
                    }`}
                  >
                    {r}
                  </button>
                ))}
              </div>
            </div>

            {errorMsg && (
              <div className="bg-red-500/10 border border-red-500/40 text-red-400 text-sm rounded px-4 py-3 text-center">
                {errorMsg}
              </div>
            )}

            <Button
              type="submit"
              variant="primary"
              className="w-full mt-4 py-3"
              isLoading={registerMutation.isPending}
            >
              CONTINUE →
            </Button>
          </form>

          <div className="mt-6 text-center text-gray-500 text-xs tracking-widest">
            <Link to="/login" className="hover:text-white transition-colors">
              ALREADY HAVE AN ACCOUNT?
            </Link>
          </div>
        </GlassCard>
      </motion.div>
    </div>
  );
}
