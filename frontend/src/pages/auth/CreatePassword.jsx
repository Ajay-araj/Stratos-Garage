import React, { useState } from 'react';
import { useNavigate, useLocation, Navigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import api from '../../services/api';
import Button from '../../components/ui/Button';
import Input from '../../components/ui/Input';
import GlassCard from '../../components/ui/GlassCard';
import { motion } from 'framer-motion';

function parseError(data) {
  if (!data) return 'Failed to create password. Please try again.';
  if (typeof data.message === 'string') return data.message;
  if (typeof data.error === 'string') return data.error;
  // DRF field-level errors
  if (data.errors && typeof data.errors === 'object') {
    const first = Object.values(data.errors)[0];
    if (Array.isArray(first)) return first[0];
  }
  if (typeof data === 'object') {
    const first = Object.values(data)[0];
    if (Array.isArray(first)) return first[0];
    if (typeof first === 'string') return first;
  }
  return 'Failed to create password. Please try again.';
}

// Password strength indicator
function PasswordStrength({ password }) {
  if (!password) return null;
  const checks = [
    password.length >= 8,
    /[A-Z]/.test(password),
    /[0-9]/.test(password),
    /[^A-Za-z0-9]/.test(password),
  ];
  const score = checks.filter(Boolean).length;
  const labels = ['', 'Weak', 'Fair', 'Good', 'Strong'];
  const colors = ['', 'bg-red-500', 'bg-yellow-500', 'bg-blue-500', 'bg-green-500'];
  return (
    <div className="space-y-1">
      <div className="flex gap-1">
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className={`h-1 flex-1 rounded-full transition-all ${
              i <= score ? colors[score] : 'bg-white/10'
            }`}
          />
        ))}
      </div>
      {score > 0 && (
        <p className={`text-xs ${score < 3 ? 'text-yellow-400' : 'text-green-400'}`}>
          {labels[score]}
        </p>
      )}
    </div>
  );
}

export default function CreatePassword() {
  const location = useLocation();
  const navigate = useNavigate();
  const token = location.state?.token || '';
  const email = location.state?.email || '';

  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  const createPasswordMutation = useMutation({
    mutationFn: (data) => api.post('users/auth/create-password/', data),
    onSuccess: () => {
      navigate('/login', {
        state: { message: 'Account activated! You can now sign in.' },
      });
    },
    onError: (error) => {
      console.error('CreatePassword error:', error.response?.status, error.response?.data);
      setErrorMsg(parseError(error.response?.data));
    },
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    setErrorMsg('');
    if (password !== passwordConfirm) {
      setErrorMsg('Passwords do not match.');
      return;
    }
    if (password.length < 8) {
      setErrorMsg('Password must be at least 8 characters.');
      return;
    }
    createPasswordMutation.mutate({
      token,
      password,
      password_confirm: passwordConfirm,
    });
  };

  if (!token) {
    return <Navigate to="/register" replace />;
  }

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
            SECURE ACCOUNT
          </h2>
          <p className="text-gray-500 text-center text-xs tracking-widest mb-2">
            STEP 3 OF 3 — CREATE PASSWORD
          </p>
          {email && (
            <p className="text-gray-400 text-center text-sm mb-8">
              Setting password for{' '}
              <span className="text-white font-medium">{email}</span>
            </p>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Input
                label="New Password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
                autoComplete="new-password"
              />
              <PasswordStrength password={password} />
            </div>

            <Input
              label="Confirm Password"
              type="password"
              value={passwordConfirm}
              onChange={(e) => setPasswordConfirm(e.target.value)}
              required
              minLength={8}
              autoComplete="new-password"
            />

            {errorMsg && (
              <div className="bg-red-500/10 border border-red-500/40 text-red-400 text-sm rounded px-4 py-3 text-center">
                {errorMsg}
              </div>
            )}

            <Button
              type="submit"
              variant="primary"
              className="w-full py-3 mt-4"
              isLoading={createPasswordMutation.isPending}
            >
              ACTIVATE ACCOUNT
            </Button>
          </form>
        </GlassCard>
      </motion.div>
    </div>
  );
}
