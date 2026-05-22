import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Mail, MapPin, Phone, Send } from 'lucide-react';
import GlassCard from '../components/ui/GlassCard';

export default function Contact() {
  const [sent, setSent] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    setSent(true);
    setTimeout(() => setSent(false), 5000);
  };

  return (
    <div className="min-h-screen pt-24 p-4 md:p-8 max-w-7xl mx-auto flex items-center justify-center">
      <div className="w-full max-w-5xl grid grid-cols-1 md:grid-cols-2 gap-12">
        {/* Info */}
        <motion.div 
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          className="flex flex-col justify-center"
        >
          <h1 className="text-4xl md:text-5xl font-display font-bold text-white uppercase tracking-widest mb-6">
            Get in Touch
          </h1>
          <p className="text-gray-400 mb-12 font-light leading-relaxed">
            Have a question about our products, orders, or want to partner with us? Drop us a message and our support team will get back to you shortly.
          </p>

          <div className="space-y-8">
            <div className="flex items-start gap-4 hover:translate-x-2 transition-transform duration-300">
              <div className="bg-white/10 p-3 rounded-full text-white">
                <Mail size={24} />
              </div>
              <div>
                <h3 className="text-white font-bold tracking-widest uppercase text-sm mb-1">Email Us</h3>
                <p className="text-gray-400">stratosgarage.dev@gmail.com</p>
              </div>
            </div>
            
            <div className="flex items-start gap-4 hover:translate-x-2 transition-transform duration-300">
              <div className="bg-white/10 p-3 rounded-full text-white">
                <MapPin size={24} />
              </div>
              <div>
                <h3 className="text-white font-bold tracking-widest uppercase text-sm mb-1">Location</h3>
                <p className="text-gray-400">Stratos Garage HQ<br/>Bangalore, Karnataka, India</p>
              </div>
            </div>

            <div className="flex items-start gap-4 hover:translate-x-2 transition-transform duration-300">
              <div className="bg-white/10 p-3 rounded-full text-white">
                <Phone size={24} />
              </div>
              <div>
                <h3 className="text-white font-bold tracking-widest uppercase text-sm mb-1">Support Call</h3>
                <p className="text-gray-400">+91 (800) 123-4567</p>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Form */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
        >
          <GlassCard className="p-8">
            <h2 className="text-2xl font-display font-bold text-white uppercase tracking-widest mb-6">
              Send a Message
            </h2>
            {sent ? (
              <div className="bg-green-500/20 border border-green-500/50 text-green-400 p-4 rounded-lg flex items-center justify-center text-center">
                Message sent successfully! We'll get back to you soon.
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-6">
                <div>
                  <label className="block text-xs font-bold text-gray-400 uppercase tracking-widest mb-2">Name</label>
                  <input required type="text" className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-white/30 transition-colors" placeholder="John Doe" />
                </div>
                <div>
                  <label className="block text-xs font-bold text-gray-400 uppercase tracking-widest mb-2">Email</label>
                  <input required type="email" className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-white/30 transition-colors" placeholder="john@example.com" />
                </div>
                <div>
                  <label className="block text-xs font-bold text-gray-400 uppercase tracking-widest mb-2">Message</label>
                  <textarea required rows="4" className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-white/30 transition-colors resize-none" placeholder="How can we help you?"></textarea>
                </div>
                <button type="submit" className="w-full bg-white text-black py-3 rounded-lg font-bold uppercase tracking-widest hover:bg-gray-200 transition-colors flex items-center justify-center gap-2">
                  <Send size={18} /> Send Message
                </button>
              </form>
            )}
          </GlassCard>
        </motion.div>
      </div>
    </div>
  );
}
