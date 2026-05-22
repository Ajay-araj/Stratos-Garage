import React from 'react';
import GlassCard from '../../components/ui/GlassCard';

export default function AdminDashboard() {
  return (
    <div className="p-8 max-w-7xl mx-auto pt-24 min-h-screen">
      <h1 className="text-3xl font-display font-bold text-white mb-8">SYSTEM ADMIN</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <GlassCard className="p-6 text-white font-bold hover:bg-white/5 transition-colors">USER MANAGEMENT</GlassCard>
        <GlassCard className="p-6 text-white font-bold hover:bg-white/5 transition-colors">SELLER VERIFICATION</GlassCard>
        <GlassCard className="p-6 text-white font-bold hover:bg-white/5 transition-colors">SYSTEM LOGS</GlassCard>
      </div>
    </div>
  );
}
