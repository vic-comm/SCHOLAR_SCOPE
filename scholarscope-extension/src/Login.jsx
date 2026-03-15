import { useState } from 'react';
import { Loader2, GraduationCap, Eye, EyeOff } from 'lucide-react';
import api from './api';

// ── Google OAuth via chrome.identity ─────────────────────────────────────────
//
// Extensions can't use normal redirect OAuth — no stable origin.
// chrome.identity.launchWebAuthFlow opens a controlled browser window,
// captures the redirect, and hands the token back to the extension.
//

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || '';

async function launchGoogleAuth() {
  const redirectUri = chrome.identity.getRedirectURL();
  const scope       = encodeURIComponent('openid email profile');

  const authUrl =
    `https://accounts.google.com/o/oauth2/auth` +
    `?client_id=${GOOGLE_CLIENT_ID}` +
    `&redirect_uri=${encodeURIComponent(redirectUri)}` +
    `&response_type=token` +
    `&scope=${scope}`;

  return new Promise((resolve, reject) => {
    chrome.identity.launchWebAuthFlow({ url: authUrl, interactive: true }, (responseUrl) => {
      if (chrome.runtime.lastError || !responseUrl) {
        reject(new Error(chrome.runtime.lastError?.message || 'Auth cancelled'));
        return;
      }
      const hash   = new URL(responseUrl).hash.slice(1);
      const params = new URLSearchParams(hash);
      const token  = params.get('access_token');
      if (!token) { reject(new Error('No access_token in response')); return; }
      resolve(token);
    });
  });
}

// ── Component ─────────────────────────────────────────────────────────────────
export default function Login({ onLoginSuccess }) {
  const [email,    setEmail]    = useState('');
  const [password, setPassword] = useState('');
  const [showPwd,  setShowPwd]  = useState(false);
  const [loading,  setLoading]  = useState(false);
  const [gLoading, setGLoading] = useState(false);
  const [error,    setError]    = useState('');

  const handleLogin = async (e) => {
    e.preventDefault();
    if (!email || !password) { setError('Email and password are required.'); return; }
    setLoading(true);
    setError('');
    try {
      const res   = await api.post('v1/auth/login/', { username: email, email, password });
      const token = res.data.key || res.data.access_token || res.data.access;
      if (token) {
        chrome.storage.local.set({ auth_token: token }, () => onLoginSuccess());
      } else {
        setError('Unexpected server response. Please try again.');
      }
    } catch (err) {
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

  const handleGoogle = async () => {
    setGLoading(true);
    setError('');
    try {
      const googleToken = await launchGoogleAuth();
      const res         = await api.post('v1/auth/google/', { access_token: googleToken });
      const token       = res.data.access;
      if (token) {
        chrome.storage.local.set({ auth_token: token }, () => onLoginSuccess());
      } else {
        setError('Unexpected server response. Please try again.');
      }
    } catch (err) {
      if (err.message === 'Auth cancelled') {
        // user closed the window — no error shown
      } else if (!err.response) {
        setError('Cannot reach server. Check your connection.');
      } else {
        setError('Google sign-in failed. Please try again.');
      }
    } finally {
      setGLoading(false);
    }
  };

  const busy = loading || gLoading;

  return (
    <div className="login-root">
      <div className="login-card">

        <div className="login-logo">
          <GraduationCap className="login-logo-icon" />
        </div>
        <h1 className="login-title">ScholarScope</h1>
        <p className="login-subtitle">Sign in to save scholarships</p>

        {error && <div className="login-error">{error}</div>}

        {/* Google */}
        <button className="google-btn" onClick={handleGoogle} disabled={busy} type="button">
          {gLoading
            ? <Loader2 className="w-4 h-4 animate-spin" />
            : <><GoogleIcon /> Continue with Google</>
          }
        </button>

        {/* Divider */}
        <div className="divider"><span>or</span></div>

        {/* Email + password */}
        <form onSubmit={handleLogin} className="login-form">
          <div className="login-field">
            <label className="login-label">Email</label>
            <input
              type="email" className="login-input" value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="you@example.com" required autoFocus disabled={busy}
            />
          </div>

          <div className="login-field">
            <label className="login-label">Password</label>
            <div className="pwd-wrapper">
              <input
                type={showPwd ? 'text' : 'password'} className="login-input"
                value={password} onChange={e => setPassword(e.target.value)}
                placeholder="••••••••" required disabled={busy}
              />
              <button type="button" className="pwd-toggle"
                onClick={() => setShowPwd(v => !v)} tabIndex={-1}>
                {showPwd ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
              </button>
            </div>
          </div>

          <button type="submit" disabled={busy} className="login-btn">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Sign In'}
          </button>
        </form>

      </div>

      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');
        .login-root {
          display:flex; align-items:center; justify-content:center;
          min-height:400px; background:#f8fafc; padding:20px;
          font-family:'DM Sans', system-ui, sans-serif;
        }
        .login-card {
          width:100%; max-width:280px; background:#fff;
          border:1px solid #e2e8f0; border-radius:12px; padding:24px 20px;
          display:flex; flex-direction:column; align-items:center; gap:4px;
        }
        .login-logo {
          width:44px; height:44px; border-radius:12px; background:#eff6ff;
          display:flex; align-items:center; justify-content:center; margin-bottom:4px;
        }
        .login-logo-icon { width:22px; height:22px; color:#2563eb; }
        .login-title    { font-size:17px; font-weight:700; color:#1e293b; margin-top:4px; }
        .login-subtitle { font-size:12px; color:#64748b; margin-bottom:8px; }
        .login-error {
          width:100%; padding:8px 10px; background:#fef2f2; color:#dc2626;
          border:1px solid #fecaca; border-radius:7px; font-size:12px;
          font-weight:500; text-align:center; margin-bottom:4px;
        }
        .google-btn {
          width:100%; padding:9px 12px; background:#fff; color:#1e293b;
          border:1px solid #e2e8f0; border-radius:7px;
          font-family:inherit; font-size:13px; font-weight:600;
          cursor:pointer; display:flex; align-items:center; justify-content:center; gap:8px;
          transition:background 0.15s, border-color 0.15s, box-shadow 0.15s;
          margin-top:4px;
        }
        .google-btn:hover:not(:disabled) {
          background:#f8fafc; border-color:#cbd5e1;
          box-shadow:0 1px 3px rgba(0,0,0,0.07);
        }
        .google-btn:disabled { opacity:0.55; cursor:not-allowed; }
        .divider {
          width:100%; display:flex; align-items:center; gap:8px;
          margin:10px 0 6px;
        }
        .divider::before, .divider::after { content:''; flex:1; height:1px; background:#e2e8f0; }
        .divider span { font-size:11px; color:#94a3b8; font-weight:500; }
        .login-form  { width:100%; display:flex; flex-direction:column; gap:12px; }
        .login-field { display:flex; flex-direction:column; gap:4px; }
        .login-label {
          font-size:11px; font-weight:600; color:#64748b;
          text-transform:uppercase; letter-spacing:0.4px;
        }
        .login-input {
          width:100%; padding:8px 10px; font-family:inherit; font-size:13px;
          color:#1e293b; background:#fff; border:1px solid #e2e8f0;
          border-radius:7px; outline:none; box-sizing:border-box;
          transition:border-color 0.15s, box-shadow 0.15s;
        }
        .login-input:focus { border-color:#2563eb; box-shadow:0 0 0 2px rgba(37,99,235,0.12); }
        .login-input:disabled { background:#f8fafc; }
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
          width:100%; padding:9px; background:#2563eb; color:#fff;
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

function GoogleIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">
      <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
      <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
      <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
      <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
      <path fill="none" d="M0 0h48v48H0z"/>
    </svg>
  );
}