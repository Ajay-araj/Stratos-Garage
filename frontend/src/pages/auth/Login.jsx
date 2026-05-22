import React, { useState } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { Eye, EyeOff } from 'lucide-react';
import api from '../../services/api';
import useAuthStore from '../../store/useAuthStore';
import Button from '../../components/ui/Button';
import Input from '../../components/ui/Input';
import GlassCard from '../../components/ui/GlassCard';
import { motion } from 'framer-motion';

function parseLoginError(data) {
  if (!data) return 'Invalid email or password.';
  if (data.needs_verification) return null; // handled by redirect
  if (typeof data.detail === 'string') return data.detail;
  if (typeof data.message === 'string') return data.message;
  if (typeof data.error === 'string') return data.error;
  // DRF non-field errors array
  if (Array.isArray(data.non_field_errors)) return data.non_field_errors[0];
  if (typeof data === 'object') {
    const first = Object.values(data)[0];
    if (Array.isArray(first)) return first[0];
    if (typeof first === 'string') return first;
  }
  return 'Invalid email or password.';
}

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const navigate = useNavigate();
  const location = useLocation();
  const setAuth = useAuthStore((state) => state.setAuth);
  const successMessage = location.state?.message || '';

  const loginMutation = useMutation({
    mutationFn: (credentials) => api.post('users/auth/login/', credentials),
    onSuccess: (response) => {
      const { user, access, refresh } = response.data;
      setAuth(user, access, refresh);
      // Redirect to intended page or home
      const from = location.state?.from || '/';
      navigate(from, { replace: true });
    },
    onError: (error) => {
      console.error('Login error:', error.response?.status, error.response?.data);
      const data = error.response?.data;

      // Backend signals email not yet verified — redirect to OTP
      if (data?.needs_verification) {
        navigate('/verify-otp', { state: { email } });
        return;
      }
      setErrorMsg(parseLoginError(data));
    },
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    setErrorMsg('');
    loginMutation.mutate({ email: email.trim(), password });
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
          {/* Header */}
          <div className="text-center mb-8">
            <h2 className="text-3xl font-display font-bold text-white tracking-widest mb-2">
              SIGN IN
            </h2>
            <p className="text-gray-500 text-xs tracking-widest uppercase">
              Premium Motorcycle Marketplace
            </p>
          </div>

          {/* Success banner (e.g. after account activation) */}
          {successMessage && (
            <div className="bg-green-500/10 border border-green-500/40 text-green-400 p-3 rounded mb-6 text-sm text-center">
              {successMessage}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Email */}
            <Input
              label="Email Address"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
            />

            {/* Password with visibility toggle */}
            <div className="relative">
              <Input
                label="Password"
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                className="absolute right-3 top-1/2 translate-y-1 text-gray-500 hover:text-white transition-colors focus:outline-none"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? (
                  <EyeOff size={18} strokeWidth={1.5} />
                ) : (
                  <Eye size={18} strokeWidth={1.5} />
                )}
              </button>
            </div>

            {/* Error message */}
            {errorMsg && (
              <div className="bg-red-500/10 border border-red-500/40 text-red-400 text-sm rounded px-4 py-3 text-center">
                {errorMsg}
              </div>
            )}

            <Button
              type="submit"
              variant="primary"
              className="w-full py-3 mt-4"
              isLoading={loginMutation.isPending}
            >
              ACCESS ACCOUNT
            </Button>
          </form>

          <div className="mt-6 flex flex-col gap-3 text-center text-gray-500 text-xs tracking-widest border-t border-white/10 pt-6">
            <Link to="/forgot-password" className="hover:text-white transition-colors">
              FORGOT PASSWORD?
            </Link>
            <Link to="/register" className="hover:text-white transition-colors">
              CREATE AN ACCOUNT
            </Link>
          </div>
        </GlassCard>
      </motion.div>
    </div>
  );
}
