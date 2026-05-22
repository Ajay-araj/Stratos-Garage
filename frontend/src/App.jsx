import React from 'react';
import { Routes, Route } from 'react-router-dom';
import Layout from './components/layout/Layout';

import Home from './pages/Home';
import Login from './pages/auth/Login';
import Register from './pages/auth/Register';
import ProductList from './pages/products/ProductList';
import ProductDetail from './pages/products/ProductDetail';
import Cart from './pages/cart/Cart';
import Checkout from './pages/cart/Checkout';
import OrderSuccess from './pages/cart/OrderSuccess';
import ScanPay from './pages/cart/ScanPay';
import Profile from './pages/dashboard/Profile';
import Orders from './pages/dashboard/Orders';
import Wishlist from './pages/dashboard/Wishlist';
import SellerDashboard from './pages/seller/Dashboard';
import AdminDashboard from './pages/admin/Dashboard';
import ForgotPassword from './pages/auth/ForgotPassword';
import VerifyOTP from './pages/auth/VerifyOTP';
import CreatePassword from './pages/auth/CreatePassword';
import AddProduct from './pages/dashboard/AddProduct';
import Contact from './pages/Contact';
import ShopCategory from './pages/shop/ShopCategory';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Home />} />
        <Route path="login" element={<Login />} />
        <Route path="register" element={<Register />} />
        <Route path="products" element={<ProductList />} />
        <Route path="products/:id" element={<ProductDetail />} />
        <Route path="cart" element={<Cart />} />
        <Route path="checkout" element={<Checkout />} />
        <Route path="orders/success" element={<OrderSuccess />} />
        <Route path="scan-pay/:orderId" element={<ScanPay />} />
        <Route path="dashboard" element={<Profile />} />
        <Route path="orders" element={<Orders />} />
        <Route path="dashboard" element={<Profile />} />
        <Route path="dashboard/wishlist" element={<Wishlist />} />
        <Route path="dashboard/add-product" element={<AddProduct />} />
        <Route path="seller" element={<SellerDashboard />} />
        <Route path="admin" element={<AdminDashboard />} />
        <Route path="forgot-password" element={<ForgotPassword />} />
        <Route path="verify-otp" element={<VerifyOTP />} />
        <Route path="create-password" element={<CreatePassword />} />
        <Route path="contact" element={<Contact />} />
        <Route path="shop/:categorySlug" element={<ShopCategory />} />

      </Route>
    </Routes>
  );
}

export default App;
