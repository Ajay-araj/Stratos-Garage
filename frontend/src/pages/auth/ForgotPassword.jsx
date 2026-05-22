import React, { useState } from 'react';
import api from '../../services/api';
import GlassCard from '../../components/ui/GlassCard';
import Input from '../../components/ui/Input';
import Button from '../../components/ui/Button';

export default function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await api.post('users/auth/password-reset/', { email });
      setSent(true);
    } catch(err) {
      alert('Error sending email');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-black px-4">
      <GlassCard className="w-full max-w-md p-8">
        <h2 className="text-2xl font-bold text-white mb-4">RESET PASSWORD</h2>
        {sent ? <p className="text-green-400">Check your email for instructions.</p> : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <Input label="Email" type="email" value={email} onChange={e => setEmail(e.target.value)} required />
            <Button type="submit" variant="primary" className="w-full">SEND LINK</Button>
          </form>
        )}
      </GlassCard>
    </div>
  );
}
