// import { useState, useEffect } from 'react';
// // import axios from 'axios'; // You can remove this if using 'api'
// import { Save, Trash2, Loader2, CheckCircle, ExternalLink, LogOut } from 'lucide-react'; // 👈 Added LogOut here
// import './App.css'; 
// import Login from './Login.jsx'; // Capitalized Login convention
// import api from './api'; // Ensure this path is correct for your extension structure

// function App() {
//   const [isAuthenticated, setIsAuthenticated] = useState(false);
//   const [checkingAuth, setCheckingAuth] = useState(true);
  
//   // Initialize as 'ready' so we don't block the Login screen. 
//   // We'll set it to 'loading' only if we actually start scraping.
//   const [status, setStatus] = useState('ready'); 
//   const [errorMessage, setErrorMessage] = useState('');

//   const [formData, setFormData] = useState({
//     title: '',
//     link: '', 
//     description: '', 
//     eligibility: '',
//     requirements: '',
//     reward: '',
//   });
  
//   // 1. Check Authentication on Mount
//   useEffect(() => {
//     chrome.storage.local.get(['auth_token'], (result) => {
//       if (result.auth_token) {
//         setIsAuthenticated(true);
//       }
//       setCheckingAuth(false);
//     });
//   }, []);

//   // 2. Load Draft + Scrape Metadata (Only runs once)
//   useEffect(() => {
//     // Only scrape if we are essentially logged in or about to be (optional optimization)
//     setStatus('loading'); 
    
//     chrome.storage.local.get(['draft'], (result) => {
//       let draft = result.draft || {};

//       // If we don't have a Title/Link yet, ask the page
//       if (!draft.title || !draft.link) {
//         chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
//           if (!tabs[0]?.id) {
//              setStatus('ready'); 
//              return;
//           }
          
//           chrome.tabs.sendMessage(tabs[0].id, { action: "SCRAPE_METADATA" }, (response) => {
//             if (chrome.runtime.lastError || !response) {
//                console.log("Scraper not ready or page not supported.");
//             } else {
//                draft = { 
//                  ...draft, 
//                  title: draft.title || response.title,
//                  link: draft.link || response.url,
//                  description: draft.description || response.description
//                };
//                chrome.storage.local.set({ draft });
//             }
//             setFormData(prev => ({ ...prev, ...draft }));
//             setStatus('ready');
//           });
//         });
//       } else {
//         setFormData(prev => ({ ...prev, ...draft }));
//         setStatus('ready');
//       }
//     });
//   }, []);

//   const handleLogout = () => {
//     chrome.storage.local.remove('auth_token');
//     setIsAuthenticated(false);
//   };

//   const handleClear = () => {
//     chrome.storage.local.remove('draft');
//     setFormData({ title: '', link: '', description: '', eligibility: '', requirements: '', reward: '' });
//     window.location.reload(); 
//   };

//   const handleChange = (e) => {
//     const { name, value } = e.target;
//     const updated = { ...formData, [name]: value };
//     setFormData(updated);
//     chrome.storage.local.set({ draft: updated });
//   };

//   const handleAutoExtract = async () => {
//     setStatus('saving');
//     setErrorMessage('');

//     chrome.storage.local.get(['auth_token'], async (result) => {
//       const token = result.auth_token;
//       if (!token) {
//         setStatus('error');
//         setErrorMessage("You are logged out.");
//         setIsAuthenticated(false);
//         return;
//       }

//       chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
//         if (!tabs[0]?.id) return;

//         // Call the DEEP_SCRAPE in content.js
//         chrome.tabs.sendMessage(tabs[0].id, { action: "DEEP_SCRAPE" }, async (response) => {
//           if (!response) {
//             setStatus('error');
//             setErrorMessage("Cannot scan this page.");
//             return;
//           }

//           try {
//             // Send the massive HTML to your new Django endpoint
//             const apiRes = await api.post('/scholarships/extract_from_html/', 
//               {
//                 title: response.title,
//                 url: response.url,
//                 raw_html: response.html
//               },
//               { headers: { 'Authorization': `Bearer ${token}` } }
//             );

//             if (apiRes.status === 200 || apiRes.status === 201) {
//               setStatus('success');
//               chrome.storage.local.remove('draft');
//             }
//           } catch (error) {
//             console.error(error);
//             setStatus('error');
//             setErrorMessage("Server failed to process HTML.");
//           }
//         });
//       });
//     });
//   };

//   const handleSave = async () => {
//     setStatus('saving');
//     setErrorMessage('');

//     chrome.storage.local.get(['auth_token'], async (result) => {
//       const token = result.auth_token;
      
//       if (!token) {
//         setStatus('error');
//         setErrorMessage("You are logged out.");
//         setIsAuthenticated(false);
//         return;
//       }

//       try {
//         const response = await api.post('/scholarships/', 
//           { ...formData, active: true },
//           {
//             headers: {
//               'Authorization': `Bearer ${token}`, 
//               'Content-Type': 'application/json'
//             }
//           }
//         );

//         if (response.status === 201 || response.status === 200) {
//           setStatus('success');
//           chrome.storage.local.remove('draft');
//         }
//       } catch (error) {
//         console.error(error);
//         setStatus('error');
//         if (error.response?.status === 401) {
//             setErrorMessage("Session expired. Please log in again.");
//             handleLogout();
//         } else {
//             setErrorMessage("Failed to save. Is server running?");
//         }
//       }
//     });
//   };

//   // --- RENDER LOGIC (Reordered for better UX) ---

//   // 1. First, check if we are still figuring out if the user is logged in
//   if (checkingAuth) {
//     return <div className="p-8 flex justify-center"><Loader2 className="animate-spin text-blue-600" /></div>;
//   }

//   // 2. If definitely not logged in, show Login immediately
//   if (!isAuthenticated) {
//     return <Login onLoginSuccess={() => setIsAuthenticated(true)} />;
//   }

//   // 3. If saving was successful, show success screen
//   if (status === 'success') {
//     return (
//       <div className="p-6 text-center w-80 flex flex-col items-center animate-in fade-in">
//         <CheckCircle className="w-16 h-16 text-green-500 mb-4" />
//         <h2 className="text-xl font-bold text-slate-800">Saved!</h2>
//         <p className="text-slate-500 text-sm mb-6">Scholarship added to dashboard.</p>
//         <button 
//           onClick={() => window.close()} 
//           className="bg-slate-100 text-slate-700 px-6 py-2 rounded-full font-medium hover:bg-slate-200"
//         >
//           Close
//         </button>
//       </div>
//     );
//   }

//   // 4. Finally, if we are authenticated but the scraper is loading
//   if (status === 'loading') {
//     return <div className="p-8 flex justify-center"><Loader2 className="animate-spin text-blue-600" /></div>;
//   }

//   return (
//     <div className="w-96 bg-slate-50 min-h-[500px] flex flex-col font-sans text-slate-800">
      
//       {/* Header */}
//       <div className="bg-white p-4 border-b flex items-center justify-between sticky top-0 z-10">
//         <div className="flex items-center gap-2">
//           <span className="font-bold text-lg text-blue-600">ScholarScope</span>
//         </div>
//         <div className="flex gap-2">
//           <button onClick={handleClear} className="text-slate-400 hover:text-red-500" title="Clear Draft">
//             <Trash2 className="w-4 h-4" />
//           </button>
//           <button onClick={handleLogout} className="text-slate-400 hover:text-blue-500" title="Sign Out">
//             <LogOut className="w-4 h-4" />
//           </button>
//         </div>
//       </div>

//       {/* Form */}
//       <div className="p-4 space-y-4 flex-1 overflow-y-auto max-h-[500px]">

//         <button 
//           onClick={handleAutoExtract}
//           disabled={status === 'saving'}
//           className="w-full bg-purple-100 text-purple-700 border border-purple-300 py-3 rounded-lg font-bold hover:bg-purple-200 transition flex items-center justify-center gap-2 mb-4"
//         >
//           ✨ Auto-Extract with AI
//         </button>

//         <div className="flex items-center gap-2 mb-4">
//             <div className="h-px bg-slate-200 flex-1"></div>
//             <span className="text-xs text-slate-400 font-medium uppercase">Or enter manually</span>
//             <div className="h-px bg-slate-200 flex-1"></div>
//         </div>

//         {status === 'error' && (
//           <div className="bg-red-50 text-red-600 p-3 rounded text-sm border border-red-200">
//             {errorMessage}
//           </div>
//         )}

//         <div>
//           <label className="label">Title</label>
//           <input 
//             className="input" 
//             name="title" 
//             value={formData.title} 
//             onChange={handleChange} 
//             placeholder="Scholarship Title"
//           />
//         </div>

//         <div>
//           <label className="label">Link</label>
//           <div className="flex gap-2">
//             <input 
//               className="input bg-slate-100 text-slate-500" 
//               name="link" 
//               value={formData.link} 
//               readOnly 
//             />
//           </div>
//         </div>

//         <div>
//           <label className="label">Reward / Amount</label>
//           <input 
//             className="input" 
//             name="reward" 
//             value={formData.reward} 
//             onChange={handleChange} 
//             placeholder="e.g. $10,000 or Full Tuition"
//           />
//         </div>

//         <div className="grid grid-cols-2 gap-3">
//           <div>
//             <label className="label">Eligibility</label>
//             <textarea 
//               className="input h-32 text-xs leading-relaxed" 
//               name="eligibility" 
//               value={formData.eligibility} 
//               onChange={handleChange}
//               placeholder="Right-click text on page to add..."
//             />
//           </div>
//           <div>
//             <label className="label">Requirements</label>
//             <textarea 
//               className="input h-32 text-xs leading-relaxed" 
//               name="requirements" 
//               value={formData.requirements} 
//               onChange={handleChange}
//               placeholder="Right-click text on page to add..."
//             />
//           </div>
//         </div>
//       </div>

//       {/* Footer Actions */}
//       <div className="p-4 bg-white border-t mt-auto">
//         <button 
//           onClick={handleSave} 
//           disabled={status === 'saving'}
//           className="w-full bg-blue-600 text-white py-2.5 rounded-lg font-bold hover:bg-blue-700 transition flex items-center justify-center gap-2 disabled:opacity-50"
//         >
//           {status === 'saving' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
//           {status === 'saving' ? 'Saving...' : 'Save to Dashboard'}
//         </button>
//       </div>
//     </div>
//   );
// }

// export default App;

import { useState, useEffect, useCallback } from 'react';
import {
  Save, Trash2, Loader2, CheckCircle, LogOut,
  Sparkles, ChevronDown, ChevronUp, AlertCircle,
  GraduationCap, Link2, DollarSign, Users, FileText, BookOpen,
  Sparkles, Loader2, AlertCircle, CheckCircle2, Info, ChevronDown, ChevronUp
} from 'lucide-react';
import Login from './Login.jsx';
import api from './api';

// ── Field wrapper ─────────────────────────────────────────────────────────────
const Field = ({ label, icon: Icon, children }) => (
  <div className="field-group">
    <label className="field-label">
      {Icon && <Icon className="field-icon" />}
      {label}
    </label>
    {children}
  </div>
);


export function useEssayDrafter({ getToken }) {
  const [essayStatus, setEssayStatus]     = useState('idle');   // idle | scanning | drafting | injecting | done | error
  const [essayStep, setEssayStep]         = useState('');
  const [essayError, setEssayError]       = useState('');
  const [essayResults, setEssayResults]   = useState(null);     // { count, completeness, drafts }

  const handleAIEssayDrafting = useCallback(async () => {
    const token = await getToken();
    if (!token) {
      setEssayStatus('error');
      setEssayError('You are not signed in.');
      return;
    }

    setEssayStatus('scanning');
    setEssayStep('Scanning for essay questions…');
    setEssayError('');
    setEssayResults(null);

    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (!tabs[0]?.id) {
        setEssayStatus('error');
        setEssayError('Cannot access this tab.');
        return;
      }

      // ── Step 1: Extract prompts from the page ─────────────────────────────
      chrome.tabs.sendMessage(tabs[0].id, { action: 'EXTRACT_ESSAY_PROMPTS' }, async (readRes) => {
        if (chrome.runtime.lastError || !readRes) {
          setEssayStatus('error');
          setEssayError('Could not read this page. Try refreshing.');
          return;
        }

        const prompts = readRes.prompts || [];
        if (prompts.length === 0) {
          setEssayStatus('error');
          setEssayError('No empty essay boxes found on this page.');
          return;
        }

        setEssayStatus('drafting');
        setEssayStep(`Found ${prompts.length} question${prompts.length > 1 ? 's' : ''}. Drafting with AI…`);

        // ── Step 2: Send to Django backend ────────────────────────────────
        try {
          const apiRes = await api.post(
            '/scholarships/draft_essays/',
            { prompts },
            { headers: { Authorization: `Bearer ${token}` } }
          );

          const { drafts = [], profile_completeness = 0 } = apiRes.data;

          const successfulDrafts = drafts.filter(d => d.draft && d.confidence !== 'failed');

          if (successfulDrafts.length === 0) {
            setEssayStatus('error');
            setEssayError('AI could not draft any essays. Is your profile filled out?');
            return;
          }

          // ── Step 3: Inject back into the page ─────────────────────────
          setEssayStatus('injecting');
          setEssayStep('Injecting drafts into the page…');

          chrome.tabs.sendMessage(
            tabs[0].id,
            { action: 'INJECT_ESSAY_DRAFTS', drafts: successfulDrafts },
            (writeRes) => {
              if (chrome.runtime.lastError) {
                setEssayStatus('error');
                setEssayError('Injection failed — try refreshing the page.');
                return;
              }

              setEssayResults({
                count:        writeRes.count,
                failed:       writeRes.failed || [],
                completeness: profile_completeness,
                drafts:       successfulDrafts,
              });
              setEssayStatus('done');
            }
          );
        } catch (err) {
          console.error('[ScholarScope] Essay drafting error:', err);
          const msg = err.response?.data?.error || 'AI drafting failed. Please try again.';
          setEssayStatus('error');
          setEssayError(msg);
        }
      });
    });
  }, [getToken]);

  const resetEssay = useCallback(() => {
    setEssayStatus('idle');
    setEssayStep('');
    setEssayError('');
    setEssayResults(null);

    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]?.id) {
        chrome.tabs.sendMessage(tabs[0].id, { action: 'CLEAR_ESSAY_HIGHLIGHTS' });
      }
    });
  }, []);

  return { essayStatus, essayStep, essayError, essayResults, handleAIEssayDrafting, resetEssay };
}


// ── UI Component ──────────────────────────────────────────────────────────────
export function EssayDraftPanel({ status, step, error, results, onDraft, onReset }) {
  const [expanded, setExpanded] = useState(false);
  const isWorking = status === 'scanning' || status === 'drafting' || status === 'injecting';

  return (
    <div className="essay-panel">
      {/* Header row */}
      <div className="essay-panel__header">
        <span className="essay-panel__label">
          <Sparkles size={13} />
          AI Essay Assistant
        </span>
        {results && (
          <button className="essay-panel__toggle" onClick={() => setExpanded(v => !v)}>
            {expanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
          </button>
        )}
      </div>

      {/* Profile completeness warning */}
      {results && results.completeness < 50 && (
        <div className="essay-panel__warning">
          <Info size={11} />
          Profile only {results.completeness}% complete — drafts may be generic.{' '}
          <a href="#" className="essay-panel__warning-link">Complete your profile</a>
        </div>
      )}

      {/* State: idle */}
      {status === 'idle' && (
        <button className="essay-btn" onClick={onDraft}>
          <Sparkles size={14} />
          Draft Essay Responses
        </button>
      )}

      {/* State: working */}
      {isWorking && (
        <div className="essay-panel__progress">
          <Loader2 size={13} className="spin" />
          <span>{step}</span>
        </div>
      )}

      {/* State: error */}
      {status === 'error' && (
        <div className="essay-panel__error">
          <AlertCircle size={13} />
          <span className="essay-panel__error-text">{error}</span>
          <button className="essay-panel__retry" onClick={onDraft}>Retry</button>
        </div>
      )}

      {/* State: done */}
      {status === 'done' && results && (
        <div className="essay-panel__done">
          <div className="essay-panel__done-summary">
            <CheckCircle2 size={14} className="essay-panel__done-icon" />
            <span>
              {results.count} draft{results.count !== 1 ? 's' : ''} injected.
              Review & edit each one.
            </span>
            <button className="essay-panel__reset" onClick={onReset} title="Clear and start over">
              Reset
            </button>
          </div>

          {results.failed?.length > 0 && (
            <p className="essay-panel__failed">
              {results.failed.length} box{results.failed.length > 1 ? 'es' : ''} could not be filled.
            </p>
          )}

          {/* Expandable draft previews */}
          {expanded && (
            <div className="essay-panel__previews">
              {results.drafts.map((d, i) => (
                <div key={d.id} className="essay-preview">
                  <div className="essay-preview__meta">
                    Essay {i + 1} &nbsp;·&nbsp; {d.word_count} words &nbsp;·&nbsp;
                    <span className={`confidence confidence--${d.confidence}`}>
                      {d.confidence}
                    </span>
                  </div>
                  <p className="essay-preview__text">{d.draft.slice(0, 120)}…</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}


// ── Main component ────────────────────────────────────────────────────────────
export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [checkingAuth, setCheckingAuth]       = useState(true);
  const [status, setStatus]                   = useState('ready'); // ready | extracting | saving | success | error
  const [errorMessage, setErrorMessage]       = useState('');
  const [extractStep, setExtractStep]         = useState('');
  const [showAdvanced, setShowAdvanced]       = useState(false);
  const [savedId, setSavedId]                 = useState(null);

  const { 
    essayStatus, essayStep, essayError, essayResults, 
    handleAIEssayDrafting, resetEssay 
  } = useEssayDrafter({ getToken });

  const [formData, setFormData] = useState({
    title: '', link: '', description: '',
    eligibility: '', requirements: '', reward: '',
    start_date: '', end_date: '',
  });

  // ── Auth check on mount ───────────────────────────────────────────────────
  useEffect(() => {
    chrome.storage.local.get(['auth_token'], (r) => {
      setIsAuthenticated(!!r.auth_token);
      setCheckingAuth(false);
    });
  }, []);

  // ── React to background context-menu writes ───────────────────────────────
  useEffect(() => {
    const handler = (changes) => {
      if (changes.draft?.newValue) {
        setFormData(prev => ({ ...prev, ...changes.draft.newValue }));
      }
    };
    chrome.storage.onChanged.addListener(handler);
    return () => chrome.storage.onChanged.removeListener(handler);
  }, []);

  // ── Load draft + page metadata on open ───────────────────────────────────
  useEffect(() => {
    chrome.storage.local.get(['draft'], (r) => {
      const draft = r.draft || {};
      if (!draft.link) {
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
          if (!tabs[0]?.id) return;
          chrome.tabs.sendMessage(tabs[0].id, { action: 'SCRAPE_METADATA' }, (res) => {
            if (chrome.runtime.lastError || !res) return;
            const merged = {
              ...draft,
              title:       draft.title       || res.title       || '',
              link:        draft.link        || res.url         || '',
              description: draft.description || res.description || '',
            };
            chrome.storage.local.set({ draft: merged });
            setFormData(prev => ({ ...prev, ...merged }));
          });
        });
      } else {
        setFormData(prev => ({ ...prev, ...draft }));
      }
    });
  }, []);

  // ── Helpers ───────────────────────────────────────────────────────────────
  const getToken = () =>
    new Promise(resolve => chrome.storage.local.get(['auth_token'], r => resolve(r.auth_token || null)));

  const logout = () => {
    chrome.storage.local.remove('auth_token');
    setIsAuthenticated(false);
  };

  const clearDraft = () => {
    chrome.storage.local.remove('draft');
    setFormData({ title:'', link:'', description:'', eligibility:'', requirements:'', reward:'', start_date:'', end_date:'' });
    setStatus('ready');
    setErrorMessage('');
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    const updated = { ...formData, [name]: value };
    setFormData(updated);
    chrome.storage.local.set({ draft: updated });
  };

  // ── AI extraction ─────────────────────────────────────────────────────────
  const handleAutoExtract = async () => {
    const token = await getToken();
    if (!token) { setStatus('error'); setErrorMessage('You are logged out.'); logout(); return; }

    setStatus('extracting');
    setExtractStep('Scanning page…');
    setErrorMessage('');

    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (!tabs[0]?.id) { setStatus('error'); setErrorMessage('No active tab found.'); return; }

      chrome.tabs.sendMessage(tabs[0].id, { action: 'DEEP_SCRAPE' }, async (response) => {
        if (chrome.runtime.lastError || !response) {
          setStatus('error');
          setErrorMessage('Cannot scan this page. Try refreshing.');
          return;
        }

        setExtractStep('Sending to AI…');
        try {
          const res = await api.post(
            '/scholarships/extract_from_html/',
            { title: response.title, url: response.url, raw_html: response.html },
            { headers: { Authorization: `Bearer ${token}` } }
          );
          if (res.status === 200 || res.status === 201) {
            setSavedId(res.data.id);
            chrome.storage.local.remove('draft');
            setStatus('success');
          }
        } catch (err) {
          console.error(err);
          const is401 = err.response?.status === 401;
          setStatus('error');
          setErrorMessage(is401 ? 'Session expired. Please log in again.' : 'AI extraction failed. Try saving manually.');
          if (is401) logout();
        }
      });
    });
  };

  // ── Manual save ───────────────────────────────────────────────────────────
  const handleSave = async () => {
    if (!formData.title?.trim()) { setStatus('error'); setErrorMessage('Title is required.'); return; }

    const token = await getToken();
    if (!token) { setStatus('error'); setErrorMessage('You are logged out.'); logout(); return; }

    setStatus('saving');
    setErrorMessage('');

    try {
      const payload = {
        ...formData,
        eligibility:  formData.eligibility  ? formData.eligibility.split('\n').filter(Boolean)  : [],
        requirements: formData.requirements ? formData.requirements.split('\n').filter(Boolean) : [],
        active: true,
      };
      const res = await api.post('/scholarships/', payload, {
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      });
      if (res.status === 201 || res.status === 200) {
        setSavedId(res.data.id);
        chrome.storage.local.remove('draft');
        setStatus('success');
      }
    } catch (err) {
      console.error(err);
      const is401 = err.response?.status === 401;
      setStatus('error');
      setErrorMessage(is401 ? 'Session expired. Please log in again.' : (err.response?.data?.detail || 'Save failed. Is the server running?'));
      if (is401) logout();
    }
  };

  // ── Render guards ─────────────────────────────────────────────────────────
  if (checkingAuth) return <CenterLoader />;
  if (!isAuthenticated) return <Login onLoginSuccess={() => setIsAuthenticated(true)} />;
  if (status === 'success') return <SuccessScreen onClose={() => window.close()} />;

  const isBusy = status === 'saving' || status === 'extracting';

  return (
    <div className="popup-root">

      {/* Header */}
      <header className="popup-header">
        <div className="header-brand">
          <GraduationCap className="brand-icon" />
          <span className="brand-name">ScholarScope</span>
        </div>
        <div className="header-actions">
          <button onClick={clearDraft} className="icon-btn" title="Clear draft" disabled={isBusy}>
            <Trash2 className="w-3.5 h-3.5" />
          </button>
          <button onClick={logout} className="icon-btn" title="Sign out" disabled={isBusy}>
            <LogOut className="w-3.5 h-3.5" />
          </button>
        </div>
      </header>

      {/* AI Button */}
      <div className="ai-section">
        <button onClick={handleAutoExtract} disabled={isBusy} className="ai-btn">
          {status === 'extracting'
            ? <><Loader2 className="w-4 h-4 animate-spin" /><span>{extractStep}</span></>
            : <><Sparkles className="w-4 h-4" /><span>Auto-Extract with AI</span></>
          }
        </button>
        {status === 'extracting' && <div className="progress-bar"><div className="progress-fill" /></div>}
      </div>
      
      <EssayDraftPanel 
        status={essayStatus}
        step={essayStep}
        error={essayError}
        results={essayResults}
        onDraft={handleAIEssayDrafting}
        onReset={resetEssay}
      />
      
      {/* Divider */}
      <div className="divider">
        <div className="divider-line" />
        <span className="divider-text">or enter manually</span>
        <div className="divider-line" />
      </div>

      {/* Error banner */}
      {status === 'error' && (
        <div className="status-error">
          <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Form */}
      <div className="form-body">
        <Field label="Title" icon={BookOpen}>
          <input className="input" name="title" value={formData.title} onChange={handleChange} placeholder="Scholarship name" />
        </Field>

        <Field label="Page URL" icon={Link2}>
          <input className="input url-input" name="link" value={formData.link} readOnly title={formData.link} />
        </Field>

        <Field label="Reward / Amount" icon={DollarSign}>
          <input className="input" name="reward" value={formData.reward} onChange={handleChange} placeholder="e.g. $10,000 or Full Tuition" />
        </Field>

        <div className="two-col">
          <Field label="Eligibility" icon={Users}>
            <textarea className="input textarea" name="eligibility" value={formData.eligibility} onChange={handleChange} placeholder="Right-click selected text to add…" />
          </Field>
          <Field label="Requirements" icon={FileText}>
            <textarea className="input textarea" name="requirements" value={formData.requirements} onChange={handleChange} placeholder="Right-click selected text to add…" />
          </Field>
        </div>

        {/* Advanced toggle */}
        <button className="advanced-toggle" onClick={() => setShowAdvanced(v => !v)}>
          {showAdvanced ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          {showAdvanced ? 'Hide' : 'Show'} dates &amp; description
        </button>

        {showAdvanced && (
          <div className="advanced-fields">
            <div className="two-col">
              <Field label="Opens"><input type="date" className="input" name="start_date" value={formData.start_date} onChange={handleChange} /></Field>
              <Field label="Deadline"><input type="date" className="input" name="end_date" value={formData.end_date} onChange={handleChange} /></Field>
            </div>
            <Field label="Description">
              <textarea className="input textarea" name="description" value={formData.description} onChange={handleChange} placeholder="Brief overview…" />
            </Field>
          </div>
        )}
      </div>

      {/* Footer */}
      <footer className="popup-footer">
        <button onClick={handleSave} disabled={isBusy} className="save-btn">
          {status === 'saving'
            ? <><Loader2 className="w-4 h-4 animate-spin" /> Saving…</>
            : <><Save className="w-4 h-4" /> Save to Dashboard</>
          }
        </button>
      </footer>
    </div>
  );
}

function CenterLoader() {
  return (
    <div style={{ display:'flex', justifyContent:'center', alignItems:'center', height:200 }}>
      <Loader2 className="w-6 h-6 animate-spin" style={{ color:'#2563eb' }} />
    </div>
  );
}

function SuccessScreen({ onClose }) {
  return (
    <div className="center-screen">
      <div className="success-ring">
        <CheckCircle className="success-icon" />
      </div>
      <h2 className="success-title">Saved!</h2>
      <p className="success-sub">Scholarship added to your dashboard.</p>
      <button onClick={onClose} className="close-btn">Close</button>
    </div>
  );
}