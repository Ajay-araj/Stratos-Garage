import React from 'react';
import { Link } from 'react-router-dom';
import Logo from '../../assets/logo';
import { Github, Linkedin, Mail } from 'lucide-react';

const Footer = () => {
  return (
    <footer className="bg-stratos-graphite border-t border-white/10 pt-16 pb-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-12 mb-12">
          
          {/* Brand */}
          <div className="space-y-4">
            <Logo className="h-8" />
            <p className="text-gray-400 text-sm leading-relaxed mt-4">
              The premier destination for motorcycle enthusiasts. Premium gear, high-performance parts, and an elite community.
            </p>
            <div className="flex space-x-4 pt-2">
              <a href="mailto:stratosgarage.dev@gmail.com" className="text-gray-400 hover:text-white hover:-translate-y-1 hover:drop-shadow-[0_0_8px_rgba(255,255,255,0.8)] transition-all duration-300"><Mail size={20} /></a>
              <a href="https://www.linkedin.com/in/ajayaraj98" target="_blank" rel="noreferrer" className="text-gray-400 hover:text-white hover:-translate-y-1 hover:drop-shadow-[0_0_8px_rgba(255,255,255,0.8)] transition-all duration-300"><Linkedin size={20} /></a>
              <a href="https://github.com/Ajay-araj" target="_blank" rel="noreferrer" className="text-gray-400 hover:text-white hover:-translate-y-1 hover:drop-shadow-[0_0_8px_rgba(255,255,255,0.8)] transition-all duration-300"><Github size={20} /></a>
            </div>
          </div>

          {/* Shop */}
          <div>
            <h3 className="text-white font-heading tracking-widest uppercase mb-6 font-semibold">Shop</h3>
            <ul className="space-y-3">
              <li><Link to="/shop/motorcycles" className="text-gray-400 hover:text-white transition-colors text-sm">Motorcycles</Link></li>
              <li><Link to="/shop/riding-gear" className="text-gray-400 hover:text-white transition-colors text-sm">Riding Gear</Link></li>
              <li><Link to="/shop/performance-parts" className="text-gray-400 hover:text-white transition-colors text-sm">Performance Parts</Link></li>
              <li><Link to="/shop/racing-collection" className="text-gray-400 hover:text-white transition-colors text-sm">Racing Collection</Link></li>
            </ul>
          </div>

          {/* Support */}
          <div>
            <h3 className="text-white font-heading tracking-widest uppercase mb-6 font-semibold">Support</h3>
            <ul className="space-y-3">
              <li><Link to="/contact" className="text-gray-400 hover:text-white transition-colors text-sm">Contact Us</Link></li>
              <li>
                <div className="flex items-center gap-2 mt-4 text-gray-400 text-sm">
                  <Mail size={16} />
                  <span>stratosgarage.dev@gmail.com</span>
                </div>
              </li>
            </ul>
          </div>
        </div>

        <div className="border-t border-white/10 pt-8 flex flex-col md:flex-row justify-between items-center gap-4">
          <p className="text-gray-500 text-sm">
            &copy; {new Date().getFullYear()} Stratos Garage. All rights reserved.
          </p>
          <div className="flex space-x-6">
            <Link to="/privacy" className="text-gray-500 hover:text-white text-sm transition-colors">Privacy Policy</Link>
            <Link to="/terms" className="text-gray-500 hover:text-white text-sm transition-colors">Terms of Service</Link>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
