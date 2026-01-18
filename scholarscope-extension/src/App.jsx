import { useState, useEffect } from 'react';
// import axios from 'axios'; // You can remove this if using 'api'
import { Save, Trash2, Loader2, CheckCircle, ExternalLink, LogOut } from 'lucide-react'; // 👈 Added LogOut here
import './App.css'; 
import Login from './Login.jsx'; // Capitalized Login convention
import api from './api'; // Ensure this path is correct for your extension structure

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [checkingAuth, setCheckingAuth] = useState(true);
  
  // Initialize as 'ready' so we don't block the Login screen. 
  // We'll set it to 'loading' only if we actually start scraping.
  const [status, setStatus] = useState('ready'); 
  const [errorMessage, setErrorMessage] = useState('');

  const [formData, setFormData] = useState({
    title: '',
    link: '', 
    description: '',
    eligibility: '',
    requirements: '',
    reward: '',
  });
  
  // 1. Check Authentication on Mount
  useEffect(() => {
    chrome.storage.local.get(['auth_token'], (result) => {
      if (result.auth_token) {
        setIsAuthenticated(true);
      }
      setCheckingAuth(false);
    });
  }, []);

  // 2. Load Draft + Scrape Metadata (Only runs once)
  useEffect(() => {
    // Only scrape if we are essentially logged in or about to be (optional optimization)
    setStatus('loading'); 
    
    chrome.storage.local.get(['draft'], (result) => {
      let draft = result.draft || {};

      // If we don't have a Title/Link yet, ask the page
      if (!draft.title || !draft.link) {
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
          if (!tabs[0]?.id) {
             setStatus('ready'); 
             return;
          }
          
          chrome.tabs.sendMessage(tabs[0].id, { action: "SCRAPE_METADATA" }, (response) => {
            if (chrome.runtime.lastError || !response) {
               console.log("Scraper not ready or page not supported.");
            } else {
               draft = { 
                 ...draft, 
                 title: draft.title || response.title,
                 link: draft.link || response.url,
                 description: draft.description || response.description
               };
               chrome.storage.local.set({ draft });
            }
            setFormData(prev => ({ ...prev, ...draft }));
            setStatus('ready');
          });
        });
      } else {
        setFormData(prev => ({ ...prev, ...draft }));
        setStatus('ready');
      }
    });
  }, []);

  const handleLogout = () => {
    chrome.storage.local.remove('auth_token');
    setIsAuthenticated(false);
  };

  const handleClear = () => {
    chrome.storage.local.remove('draft');
    setFormData({ title: '', link: '', description: '', eligibility: '', requirements: '', reward: '' });
    window.location.reload(); 
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    const updated = { ...formData, [name]: value };
    setFormData(updated);
    chrome.storage.local.set({ draft: updated });
  };

  const handleSave = async () => {
    setStatus('saving');
    setErrorMessage('');

    chrome.storage.local.get(['auth_token'], async (result) => {
      const token = result.auth_token;
      
      if (!token) {
        setStatus('error');
        setErrorMessage("You are logged out.");
        setIsAuthenticated(false);
        return;
      }

      try {
        const response = await api.post('/scholarships/', 
          { ...formData, active: true },
          {
            headers: {
              'Authorization': `Bearer ${token}`, 
              'Content-Type': 'application/json'
            }
          }
        );

        if (response.status === 201 || response.status === 200) {
          setStatus('success');
          chrome.storage.local.remove('draft');
        }
      } catch (error) {
        console.error(error);
        setStatus('error');
        if (error.response?.status === 401) {
            setErrorMessage("Session expired. Please log in again.");
            handleLogout();
        } else {
            setErrorMessage("Failed to save. Is server running?");
        }
      }
    });
  };

  // --- RENDER LOGIC (Reordered for better UX) ---

  // 1. First, check if we are still figuring out if the user is logged in
  if (checkingAuth) {
    return <div className="p-8 flex justify-center"><Loader2 className="animate-spin text-blue-600" /></div>;
  }

  // 2. If definitely not logged in, show Login immediately
  if (!isAuthenticated) {
    return <Login onLoginSuccess={() => setIsAuthenticated(true)} />;
  }

  // 3. If saving was successful, show success screen
  if (status === 'success') {
    return (
      <div className="p-6 text-center w-80 flex flex-col items-center animate-in fade-in">
        <CheckCircle className="w-16 h-16 text-green-500 mb-4" />
        <h2 className="text-xl font-bold text-slate-800">Saved!</h2>
        <p className="text-slate-500 text-sm mb-6">Scholarship added to dashboard.</p>
        <button 
          onClick={() => window.close()} 
          className="bg-slate-100 text-slate-700 px-6 py-2 rounded-full font-medium hover:bg-slate-200"
        >
          Close
        </button>
      </div>
    );
  }

  // 4. Finally, if we are authenticated but the scraper is loading
  if (status === 'loading') {
    return <div className="p-8 flex justify-center"><Loader2 className="animate-spin text-blue-600" /></div>;
  }

  return (
    <div className="w-96 bg-slate-50 min-h-[500px] flex flex-col font-sans text-slate-800">
      
      {/* Header */}
      <div className="bg-white p-4 border-b flex items-center justify-between sticky top-0 z-10">
        <div className="flex items-center gap-2">
          <span className="font-bold text-lg text-blue-600">ScholarScope</span>
        </div>
        <div className="flex gap-2">
          <button onClick={handleClear} className="text-slate-400 hover:text-red-500" title="Clear Draft">
            <Trash2 className="w-4 h-4" />
          </button>
          <button onClick={handleLogout} className="text-slate-400 hover:text-blue-500" title="Sign Out">
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Form */}
      <div className="p-4 space-y-4 flex-1 overflow-y-auto max-h-[500px]">
        {status === 'error' && (
          <div className="bg-red-50 text-red-600 p-3 rounded text-sm border border-red-200">
            {errorMessage}
          </div>
        )}

        <div>
          <label className="label">Title</label>
          <input 
            className="input" 
            name="title" 
            value={formData.title} 
            onChange={handleChange} 
            placeholder="Scholarship Title"
          />
        </div>

        <div>
          <label className="label">Link</label>
          <div className="flex gap-2">
            <input 
              className="input bg-slate-100 text-slate-500" 
              name="link" 
              value={formData.link} 
              readOnly 
            />
          </div>
        </div>

        <div>
          <label className="label">Reward / Amount</label>
          <input 
            className="input" 
            name="reward" 
            value={formData.reward} 
            onChange={handleChange} 
            placeholder="e.g. $10,000 or Full Tuition"
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">Eligibility</label>
            <textarea 
              className="input h-32 text-xs leading-relaxed" 
              name="eligibility" 
              value={formData.eligibility} 
              onChange={handleChange}
              placeholder="Right-click text on page to add..."
            />
          </div>
          <div>
            <label className="label">Requirements</label>
            <textarea 
              className="input h-32 text-xs leading-relaxed" 
              name="requirements" 
              value={formData.requirements} 
              onChange={handleChange}
              placeholder="Right-click text on page to add..."
            />
          </div>
        </div>
      </div>

      {/* Footer Actions */}
      <div className="p-4 bg-white border-t mt-auto">
        <button 
          onClick={handleSave} 
          disabled={status === 'saving'}
          className="w-full bg-blue-600 text-white py-2.5 rounded-lg font-bold hover:bg-blue-700 transition flex items-center justify-center gap-2 disabled:opacity-50"
        >
          {status === 'saving' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          {status === 'saving' ? 'Saving...' : 'Save to Dashboard'}
        </button>
      </div>
    </div>
  );
}

export default App;