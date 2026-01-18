// src/components/Login.jsx
import { useState } from 'react';
import axios from 'axios';
import { Loader2 } from 'lucide-react';
import api from '../api';
export default function Login({ onLoginSuccess }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      // Adjust URL to match your Django Backend
      const res = await api.post("/v1/auth/login/", { 
                email, 
                password});
        

      // dj-rest-auth usually returns: { "key": "..." } or { "access": "..." }
      const token = res.data.key || res.data.access_token || res.data.access;
      
      if (token) {
        // Save to Extension Storage (Not localStorage!)
        chrome.storage.local.set({ 'auth_token': token }, () => {
          onLoginSuccess();
        });
      } else {
        setError("Invalid response from server.");
      }
    } catch (err) {
      console.error(err);
      setError("Invalid credentials. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center h-[400px] p-6 bg-slate-50">
      <div className="w-full max-w-xs bg-white p-6 rounded-lg shadow-sm border border-slate-200">
        <h2 className="text-xl font-bold text-center text-blue-600 mb-6">ScholarScope</h2>
        
        {error && <p className="text-red-500 text-xs mb-3 text-center">{error}</p>}
        
        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className="text-xs font-bold text-slate-500 uppercase">Email</label>
            <input 
              type="email" 
              className="w-full p-2 border rounded text-sm mt-1 focus:ring-2 focus:ring-blue-500 outline-none"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          
          <div>
            <label className="text-xs font-bold text-slate-500 uppercase">Password</label>
            <input 
              type="password" 
              className="w-full p-2 border rounded text-sm mt-1 focus:ring-2 focus:ring-blue-500 outline-none"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          <button 
            type="submit" 
            disabled={loading}
            className="w-full bg-blue-600 text-white py-2 rounded font-bold hover:bg-blue-700 disabled:opacity-50 flex justify-center"
          >
            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : "Sign In"}
          </button>
        </form>
      </div>
    </div>
  );
}