import React from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import Button from '../components/ui/Button';

export default function Home() {
  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden bg-black">
      <div className="absolute inset-0 bg-gradient-to-br from-gray-900 to-black z-0" />
      <div className="relative z-10 text-center max-w-4xl px-4 pt-16">
        <motion.h1 
          initial={{ opacity: 0, y: 30 }} 
          animate={{ opacity: 1, y: 0 }} 
          transition={{ duration: 0.8 }}
          className="text-6xl md:text-8xl font-display font-bold text-white mb-6 tracking-tighter"
        >
          PURE ADRENALINE.
        </motion.h1>
        <motion.p 
          initial={{ opacity: 0 }} 
          animate={{ opacity: 1 }} 
          transition={{ duration: 0.8, delay: 0.3 }}
          className="text-xl md:text-2xl text-gray-400 mb-10 font-light"
        >
          Premium motorcycle performance parts & riding gear.
        </motion.p>
        <motion.div 
          initial={{ opacity: 0, y: 20 }} 
          animate={{ opacity: 1, y: 0 }} 
          transition={{ duration: 0.8, delay: 0.6 }}
        >
          <Link to="/products">
            <Button variant="primary" className="text-lg px-8 py-4">
              EXPLORE COLLECTION
            </Button>
          </Link>
        </motion.div>
      </div>
    </div>
  );
}
