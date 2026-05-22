import React from 'react';
import { Outlet } from 'react-router-dom';
import Navbar from './Navbar';
import Footer from './Footer';

const Layout = () => {
  return (
    <div className="min-h-screen flex flex-col selection:bg-white/30 selection:text-white">
      <Navbar />
      
      <main className="flex-grow pt-20"> {/* pt-20 to account for fixed navbar */}
        <Outlet />
      </main>
      
      <Footer />
    </div>
  );
};

export default Layout;
