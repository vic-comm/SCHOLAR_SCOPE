import { useState, useEffect } from 'react';
import axios from 'axios';
import { Save, Trash2, Loader2, CheckCircle, ExternalLink } from 'lucide-react';
import './App.css'; // We'll add some basic CSS in Step 7

function App() {
  const [formData, setFormData] = useState({
    title: '',
    link: '', // Django expects 'link', not 'url'
    description: '',
    eligibility: '',
    requirements: '',
    reward: '',
  });
  
  const [status, setStatus] = useState('loading'); // loading | ready | saving | success | error
  const [errorMessage, setErrorMessage] = useState('');

  // 1. Initialize: Load Draft + Scrape Metadata
  useEffect(() => {
    // A. Check our "Basket" (Storage)
    chrome.storage.local.get(['draft'], (result) => {
      let draft = result.draft || {};

      // B. If we don't have a Title/Link yet, ask the page
      if (!draft.title || !draft.link) {
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
          if (!tabs[0]?.id) return;
          
          chrome.tabs.sendMessage(tabs[0].id, { action: "SCRAPE_METADATA" }, (response) => {
            // If the content script isn't ready (e.g. browser settings page), response might be undefined
            if (chrome.runtime.lastError || !response) {
               console.log("Scraper not ready or page not supported.");
            } else {
               // Merge page data with our draft
               draft = { 
                 ...draft, 
                 title: draft.title || response.title,
                 link: draft.link || response.url,
                 description: draft.description || response.description
               };
               
               // Save the merged version back to storage so we remember it
               chrome.storage.local.set({ draft });
            }
            // Update UI
            setFormData(prev => ({ ...prev, ...draft }));
            setStatus('ready');
          });
        });
      } else {
        // We already have data, just show it
        setFormData(prev => ({ ...prev, ...draft }));
        setStatus('ready');
      }
    });
  }, []);

  // 2. Handle Input Changes
  const handleChange = (e) => {
    const { name, value } = e.target;
    const updated = { ...formData, [name]: value };
    setFormData(updated);
    // Auto-save to local storage as you type (prevent data loss)
    chrome.storage.local.set({ draft: updated });
  };

  // 3. Clear Draft (Start Over)
  const handleClear = () => {
    chrome.storage.local.remove('draft');
    setFormData({ title: '', link: '', description: '', eligibility: '', requirements: '', reward: '' });
    // Re-trigger scrape metadata
    window.location.reload(); 
  };

  // 4. Submit to Django
  const handleSave = async () => {
    setStatus('saving');
    setErrorMessage('');

    try {
      // NOTE: Ensure your Django server is running!
      // If using JWT, you'll need to handle auth headers here. 
      // For now, we assume standard session or you are testing locally.
      const response = await axios.post('http://127.0.0.1:8000/api/scholarships/', {
        ...formData,
        active: true, // Default to active
        // You might need to add default dates or tags if your backend requires them
      });

      if (response.status === 201) {
        setStatus('success');
        chrome.storage.local.remove('draft'); // Clear basket on success
      }
    } catch (error) {
      console.error(error);
      setStatus('error');
      setErrorMessage("Failed to save. Is the server running?");
    }
  };

  // --- RENDER HELPERS ---

  if (status === 'loading') {
    return <div className="p-8 flex justify-center"><Loader2 className="animate-spin text-blue-600" /></div>;
  }

  if (status === 'success') {
    return (
      <div className="p-6 text-center w-80 flex flex-col items-center animate-in fade-in">
        <CheckCircle className="w-16 h-16 text-green-500 mb-4" />
        <h2 className="text-xl font-bold text-slate-800">Saved!</h2>
        <p className="text-slate-500 text-sm mb-6">Scholarship added to dashboard.</p>
        <button 
          onClick={() => window.close()} // Close the popup
          className="bg-slate-100 text-slate-700 px-6 py-2 rounded-full font-medium hover:bg-slate-200"
        >
          Close
        </button>
      </div>
    );
  }

  return (
    <div className="w-96 bg-slate-50 min-h-[500px] flex flex-col font-sans text-slate-800">
      
      {/* Header */}
      <div className="bg-white p-4 border-b flex items-center justify-between sticky top-0 z-10">
        <div className="flex items-center gap-2">
          <span className="font-bold text-lg text-blue-600">ScholarScope</span>
          <span className="bg-blue-100 text-blue-700 text-[10px] px-2 py-0.5 rounded-full font-bold">DRAFT</span>
        </div>
        <button onClick={handleClear} className="text-slate-400 hover:text-red-500" title="Clear Draft">
          <Trash2 className="w-4 h-4" />
        </button>
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