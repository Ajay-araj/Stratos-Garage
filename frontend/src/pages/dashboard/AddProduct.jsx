import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, Plus, X } from 'lucide-react';
import api from '../../services/api';
import useAuthStore from '../../store/useAuthStore';

export default function AddProduct() {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const [categories, setCategories] = useState([]);
  
  const [formData, setFormData] = useState({
    name: '',
    category_id: '',
    base_price: '',
    description: '',
    short_description: '',
    initial_stock: '1',
    sku: '',
  });

  const [images, setImages] = useState([]);
  const [previewUrls, setPreviewUrls] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);  // null | array of {field, msg}
  const [success, setSuccess] = useState('');

  useEffect(() => {
    if (!user) {
      navigate('/login');
      return;
    }
    const fetchCategories = async () => {
      try {
        const res = await api.get('/products/categories/flat/');
        setCategories(res.data);
      } catch (err) {
        console.error('Failed to load categories', err);
      }
    };
    fetchCategories();
  }, [user, navigate]);

  const handleImageChange = (e) => {
    const files = Array.from(e.target.files);
    setImages(files);
    
    // Generate previews
    const urls = files.map(file => URL.createObjectURL(file));
    setPreviewUrls(urls);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess('');

    try {
      const formDataToSend = new FormData();
      formDataToSend.append('name', formData.name);
      formDataToSend.append('category', formData.category_id);
      formDataToSend.append('price', formData.base_price);
      formDataToSend.append('stock', formData.initial_stock);
      formDataToSend.append('description', formData.description);
      formDataToSend.append('short_description', formData.short_description || formData.description.substring(0, 100));
      if (formData.sku) {
        formDataToSend.append('sku', formData.sku);
      }

      images.forEach((image) => {
        formDataToSend.append('images', image);
      });

      await api.post('/products/add/', formDataToSend, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setSuccess('Product uploaded successfully!');
      setTimeout(() => navigate('/products'), 2000);

    } catch (err) {
      console.error(err);
      if (err.response?.data?.errors) {
         setError([{ field: 'Error', msg: JSON.stringify(err.response.data.errors) }]);
      } else {
        const data = err.response?.data;
        if (!data) {
          setError([{ field: 'Error', msg: 'Network error — check if the backend is running.' }]);
        } else if (typeof data === 'string') {
          setError([{ field: 'Error', msg: data }]);
        } else if (data.detail) {
          setError([{ field: 'Permission', msg: data.detail }]);
        } else if (typeof data === 'object') {
          const errs = Object.entries(data).map(([k, v]) => ({
            field: k.replace(/_/g, ' ').toUpperCase(),
            msg: Array.isArray(v) ? v.join(', ') : String(v),
          }));
          setError(errs);
        } else {
          setError([{ field: 'Error', msg: 'Upload failed. Please try again.' }]);
        }
      }
    } finally {
      setLoading(false);
    }
  };


  return (
    <div className="pt-24 pb-16 px-4 max-w-4xl mx-auto">
      <h1 className="text-3xl font-display font-bold text-white tracking-widest mb-8">ADD NEW PRODUCT</h1>
      
      {error && (
        <div className="bg-red-900/50 border border-red-500/50 text-red-200 p-4 rounded-lg mb-6 space-y-1">
          {Array.isArray(error) ? (
            error.map((e, i) => (
              <div key={i} className="flex gap-2 text-sm">
                <span className="text-red-400 font-bold uppercase tracking-widest text-[10px] pt-0.5 whitespace-nowrap">{e.field}:</span>
                <span>{e.msg}</span>
              </div>
            ))
          ) : (
            <p className="text-sm">{error}</p>
          )}
        </div>
      )}
      {success && <div className="bg-green-900/50 border border-green-500/50 text-green-200 p-4 rounded-lg mb-6">{success}</div>}

      <form onSubmit={handleSubmit} className="bg-white/5 backdrop-blur-md border border-white/10 p-8 rounded-2xl space-y-6">
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-2">
            <label className="text-sm font-semibold text-gray-300 uppercase tracking-wider">Product Name</label>
            <input required type="text" value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})} className="w-full bg-black/50 border border-white/10 rounded-lg p-3 text-white focus:border-white focus:ring-1 focus:ring-white transition-all outline-none" placeholder="e.g. Akrapovič Slip-On Line" />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-semibold text-gray-300 uppercase tracking-wider">Category</label>
            <select required value={formData.category_id} onChange={e => setFormData({...formData, category_id: e.target.value})} className="w-full bg-black/50 border border-white/10 rounded-lg p-3 text-white focus:border-white focus:ring-1 focus:ring-white transition-all outline-none">
              <option value="">Select Category...</option>
              {categories.map(c => (
                <option key={c.id} value={c.id}>{c.full_name || c.name}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="space-y-2">
            <label className="text-sm font-semibold text-gray-300 uppercase tracking-wider">Price (INR)</label>
            <input required type="number" min="0.01" step="0.01" value={formData.base_price} onChange={e => setFormData({...formData, base_price: e.target.value})} className="w-full bg-black/50 border border-white/10 rounded-lg p-3 text-white focus:border-white focus:ring-1 focus:ring-white transition-all outline-none" placeholder="0.00" />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-semibold text-gray-300 uppercase tracking-wider">Initial Stock</label>
            <input required type="number" min="0" value={formData.initial_stock} onChange={e => setFormData({...formData, initial_stock: e.target.value})} className="w-full bg-black/50 border border-white/10 rounded-lg p-3 text-white focus:border-white focus:ring-1 focus:ring-white transition-all outline-none" placeholder="10" />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-semibold text-gray-300 uppercase tracking-wider">SKU (Optional)</label>
            <input type="text" value={formData.sku} onChange={e => setFormData({...formData, sku: e.target.value})} className="w-full bg-black/50 border border-white/10 rounded-lg p-3 text-white focus:border-white focus:ring-1 focus:ring-white transition-all outline-none" placeholder="Auto-generated if blank" />
          </div>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-semibold text-gray-300 uppercase tracking-wider">Description</label>
          <textarea required value={formData.description} onChange={e => setFormData({...formData, description: e.target.value})} rows={4} className="w-full bg-black/50 border border-white/10 rounded-lg p-3 text-white focus:border-white focus:ring-1 focus:ring-white transition-all outline-none resize-none" placeholder="Describe the product details, specs, etc..." />
        </div>

        <div className="space-y-4">
          <label className="text-sm font-semibold text-gray-300 uppercase tracking-wider">Product Images</label>
          
          <div className="flex items-center justify-center w-full">
            <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-white/10 border-dashed rounded-xl cursor-pointer hover:bg-white/5 transition-all">
              <div className="flex flex-col items-center justify-center pt-5 pb-6">
                <Upload className="w-8 h-8 mb-3 text-gray-400" />
                <p className="mb-2 text-sm text-gray-400"><span className="font-bold text-white">Click to upload</span> or drag and drop</p>
                <p className="text-xs text-gray-500">PNG, JPG, WEBP (Max. 3 images)</p>
              </div>
              <input type="file" multiple accept="image/*" className="hidden" onChange={handleImageChange} />
            </label>
          </div>

          {previewUrls.length > 0 && (
            <div className="grid grid-cols-3 gap-4 mt-4">
              {previewUrls.map((url, i) => (
                <div key={i} className="relative aspect-square rounded-lg overflow-hidden border border-white/10 group">
                  <img src={url} alt={`preview ${i}`} className="w-full h-full object-cover" />
                  <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                    <span className="text-xs font-bold tracking-widest text-white">PREVIEW {i+1}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="pt-4 border-t border-white/10 flex justify-end">
          <button type="submit" disabled={loading} className="bg-white text-black px-8 py-3 rounded-lg font-bold tracking-widest uppercase hover:bg-gray-200 transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed">
            {loading ? 'Uploading...' : (
              <>
                <Plus size={20} />
                Add Product
              </>
            )}
          </button>
        </div>

      </form>
    </div>
  );
}
