// // src/components/Login.jsx
// import { useState } from 'react';
// import axios from 'axios';
// import { Loader2 } from 'lucide-react';
// import api from '../api';
// export default function Login({ onLoginSuccess }) {
//   const [email, setEmail] = useState('');
//   const [password, setPassword] = useState('');
//   const [loading, setLoading] = useState(false);
//   const [error, setError] = useState('');

//   const handleLogin = async (e) => {
//     e.preventDefault();
//     setLoading(true);
//     setError('');

//     try {
//       // Adjust URL to match your Django Backend
//       const res = await api.post("/v1/auth/login/", { 
//                 email, 
//                 password});
        

//       // dj-rest-auth usually returns: { "key": "..." } or { "access": "..." }
//       const token = res.data.key || res.data.access_token || res.data.access;
      
//       if (token) {
//         // Save to Extension Storage (Not localStorage!)
//         chrome.storage.local.set({ 'auth_token': token }, () => {
//           onLoginSuccess();
//         });
//       } else {
//         setError("Invalid response from server.");
//       }
//     } catch (err) {
//       console.error(err);
//       setError("Invalid credentials. Please try again.");
//     } finally {
//       setLoading(false);
//     }
//   };

//   return (
//     <div className="flex flex-col items-center justify-center h-[400px] p-6 bg-slate-50">
//       <div className="w-full max-w-xs bg-white p-6 rounded-lg shadow-sm border border-slate-200">
//         <h2 className="text-xl font-bold text-center text-blue-600 mb-6">ScholarScope</h2>
        
//         {error && <p className="text-red-500 text-xs mb-3 text-center">{error}</p>}
        
//         <form onSubmit={handleLogin} className="space-y-4">
//           <div>
//             <label className="text-xs font-bold text-slate-500 uppercase">Email</label>
//             <input 
//               type="email" 
//               className="w-full p-2 border rounded text-sm mt-1 focus:ring-2 focus:ring-blue-500 outline-none"
//               value={email}
//               onChange={(e) => setEmail(e.target.value)}
//               required
//             />
//           </div>
          
//           <div>
//             <label className="text-xs font-bold text-slate-500 uppercase">Password</label>
//             <input 
//               type="password" 
//               className="w-full p-2 border rounded text-sm mt-1 focus:ring-2 focus:ring-blue-500 outline-none"
//               value={password}
//               onChange={(e) => setPassword(e.target.value)}
//               required
//             />
//           </div>

//           <button 
//             type="submit" 
//             disabled={loading}
//             className="w-full bg-blue-600 text-white py-2 rounded font-bold hover:bg-blue-700 disabled:opacity-50 flex justify-center"
//           >
//             {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : "Sign In"}
//           </button>
//         </form>
//       </div>
//     </div>
//   );
// }

import { useState } from 'react';
import { Loader2, GraduationCap, Eye, EyeOff } from 'lucide-react';
import api from './api';

export default function Login({ onLoginSuccess }) {
  const [email, setEmail]       = useState('');
  const [password, setPassword] = useState('');
  const [showPwd, setShowPwd]   = useState(false);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState('');

  const handleLogin = async (e) => {
    e.preventDefault();
    if (!email || !password) { setError('Email and password are required.'); return; }
    setLoading(true);
    setError('');

    try {
      const res = await api.post('/v1/auth/login/', { email, password });
      const token = res.data.key || res.data.access_token || res.data.access;

      if (token) {
        chrome.storage.local.set({ auth_token: token }, () => onLoginSuccess());
      } else {
        setError('Unexpected server response. Please try again.');
      }
    } catch (err) {
      console.error(err);
      if (err.response?.status === 401 || err.response?.status === 400) {
        setError('Invalid email or password.');
      } else if (!err.response) {
        setError('Cannot reach server. Check your connection.');
      } else {
        setError('Login failed. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-root">
      <div className="login-card">
        <div className="login-logo">
          <GraduationCap className="login-logo-icon" />
        </div>
        <h1 className="login-title">ScholarScope</h1>
        <p className="login-subtitle">Sign in to save scholarships</p>

        {error && <div className="login-error">{error}</div>}

        <form onSubmit={handleLogin} className="login-form">
          <div className="login-field">
            <label className="login-label">Email</label>
            <input
              type="email"
              className="login-input"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
              autoFocus
            />
          </div>

          <div className="login-field">
            <label className="login-label">Password</label>
            <div className="pwd-wrapper">
              <input
                type={showPwd ? 'text' : 'password'}
                className="login-input"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="••••••••"
                required
              />
              <button type="button" className="pwd-toggle" onClick={() => setShowPwd(v => !v)} tabIndex={-1}>
                {showPwd ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
              </button>
            </div>
          </div>

          <button type="submit" disabled={loading} className="login-btn">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Sign In'}
          </button>
        </form>
      </div>

      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');
        .login-root {
          display:flex; align-items:center; justify-content:center;
          height:400px; background:#f8fafc; padding:20px;
          font-family:'DM Sans', system-ui, sans-serif;
        }
        .login-card {
          width:100%; max-width:280px;
          background:#fff; border:1px solid #e2e8f0; border-radius:12px;
          padding:24px 20px;
          display:flex; flex-direction:column; align-items:center; gap:4px;
        }
        .login-logo {
          width:44px; height:44px; border-radius:12px; background:#eff6ff;
          display:flex; align-items:center; justify-content:center; margin-bottom:4px;
        }
        .login-logo-icon { width:22px; height:22px; color:#2563eb; }
        .login-title     { font-size:17px; font-weight:700; color:#1e293b; margin-top:4px; }
        .login-subtitle  { font-size:12px; color:#64748b; margin-bottom:12px; }
        .login-error {
          width:100%; padding:8px 10px;
          background:#fef2f2; color:#dc2626; border:1px solid #fecaca;
          border-radius:7px; font-size:12px; font-weight:500;
          text-align:center; margin-bottom:4px;
        }
        .login-form  { width:100%; display:flex; flex-direction:column; gap:12px; }
        .login-field { display:flex; flex-direction:column; gap:4px; }
        .login-label { font-size:11px; font-weight:600; color:#64748b; text-transform:uppercase; letter-spacing:0.4px; }
        .login-input {
          width:100%; padding:8px 10px;
          font-family:inherit; font-size:13px; color:#1e293b;
          background:#fff; border:1px solid #e2e8f0; border-radius:7px;
          outline:none; transition:border-color 0.15s, box-shadow 0.15s;
        }
        .login-input:focus    { border-color:#2563eb; box-shadow:0 0 0 2px rgba(37,99,235,0.12); }
        .login-input::placeholder { color:#94a3b8; }
        .pwd-wrapper { position:relative; }
        .pwd-wrapper .login-input { padding-right:32px; }
        .pwd-toggle {
          position:absolute; right:8px; top:50%; transform:translateY(-50%);
          background:none; border:none; cursor:pointer; color:#94a3b8;
          display:flex; padding:2px; transition:color 0.15s;
        }
        .pwd-toggle:hover { color:#64748b; }
        .login-btn {
          width:100%; padding:9px;
          background:#2563eb; color:#fff;
          font-family:inherit; font-size:13px; font-weight:600;
          border:none; border-radius:7px; cursor:pointer;
          display:flex; align-items:center; justify-content:center;
          transition:background 0.15s, opacity 0.15s; margin-top:2px;
        }
        .login-btn:hover:not(:disabled) { background:#1d4ed8; }
        .login-btn:disabled { opacity:0.55; cursor:not-allowed; }
      `}</style>
    </div>
  );
}