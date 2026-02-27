import { useState, useEffect, useCallback, Component } from 'react';
import {
  Save, Trash2, Loader2, CheckCircle, LogOut,
  Sparkles, ChevronDown, ChevronUp, AlertCircle,
  GraduationCap, Link2, DollarSign, Users, FileText, BookOpen
} from 'lucide-react';
import Login from './Login.jsx';
import api from './api';
import ReviewModal, { useReviewModal } from './components/ReviewModal';

// ─── FIX 1 ────────────────────────────────────────────────────────────────────
// App.jsx only imported `useEssayDrafter` and `injectApprovedDrafts`, but then
// used <EssayDraftPanel /> as a JSX component. React sees an undefined variable
// and throws "EssayDraftPanel is not defined", which crashes the entire render
// tree and produces a blank white popup. Added EssayDraftPanel to the import.
import {
  useEssayDrafter,
  injectApprovedDrafts,
  EssayDraftPanel,
} from './components/EssayDraftPanel';

import './components/ReviewModal.css';

// ─── FIX 2 ────────────────────────────────────────────────────────────────────
// Without an error boundary, any render crash (like the missing import above)
// silently unmounts the entire React tree — the user sees a blank white box with
// no hint of what went wrong. This class component catches render errors and
// shows a readable message with a reload button instead.
class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }
  static getDerivedStateFromError(error) {
    return { error };
  }
  componentDidCatch(error, info) {
    console.error('[ScholarScope] Render crash:', error, info.componentStack);
  }
  render() {
    if (this.state.error) {
      return (
        <div style={{
          padding: '18px 16px', fontFamily: 'system-ui', background: '#0f1117',
          color: '#e8ecf4', minHeight: 120,
        }}>
          <p style={{ color: '#f87171', fontWeight: 600, marginBottom: 6, fontSize: 13 }}>
            Something went wrong
          </p>
          <p style={{ color: '#7a859e', fontSize: 11, marginBottom: 14, wordBreak: 'break-word' }}>
            {this.state.error.message}
          </p>
          <button
            onClick={() => this.setState({ error: null })}
            style={{
              background: '#1d4ed8', color: '#fff', border: 'none',
              borderRadius: 6, padding: '6px 14px', fontSize: 12, cursor: 'pointer',
            }}
          >
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

// ─── FIX 3 ────────────────────────────────────────────────────────────────────
// getToken was defined inside the component body in the original, meaning a new
// function reference was created on every render. This breaks useCallback
// dependency arrays in the child hooks (useEssayDrafter) because the reference
// changes every render, causing stale closures. Defined at module level so the
// reference is stable for the lifetime of the page.
const getToken = () =>
  new Promise(resolve =>
    chrome.storage.local.get(['auth_token'], r => resolve(r.auth_token || null))
  );

// ── Field layout helper ───────────────────────────────────────────────────────
const Field = ({ label, icon: Icon, children }) => (
  <div className="field-group">
    <label className="field-label">
      {Icon && <Icon className="field-icon" size={13} />}
      {label}
    </label>
    {children}
  </div>
);

// ── Main App ──────────────────────────────────────────────────────────────────
function AppInner() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [checkingAuth,    setCheckingAuth]    = useState(true);
  const [status,          setStatus]          = useState('ready');
  const [errorMessage,    setErrorMessage]    = useState('');
  const [extractStep,     setExtractStep]     = useState('');
  const [showAdvanced,    setShowAdvanced]    = useState(false);
  const [savedId,         setSavedId]         = useState(null);

  const reviewModal = useReviewModal();
  const { essayStatus, essayStep, essayError, handleAIEssayDrafting, resetEssay } =
    useEssayDrafter({ getToken, reviewModal });

  const [formData, setFormData] = useState({
    title: '', link: '', description: '',
    eligibility: '', requirements: '', reward: '',
    start_date: '', end_date: '',
  });

  // Auth check on mount
  useEffect(() => {
    chrome.storage.local.get(['auth_token'], (r) => {
      setIsAuthenticated(!!r.auth_token);
      setCheckingAuth(false);
    });
  }, []);

  // React to context-menu writes from the background script
  useEffect(() => {
    const handler = (changes) => {
      if (changes.draft?.newValue) {
        setFormData(prev => ({ ...prev, ...changes.draft.newValue }));
      }
    };
    chrome.storage.onChanged.addListener(handler);
    return () => chrome.storage.onChanged.removeListener(handler);
  }, []);

  // Load saved draft + page metadata when popup opens
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

  // ─── FIX 4 ──────────────────────────────────────────────────────────────────
  // Original handleInjectApproved passed a callback to injectApprovedDrafts but
  // injectApprovedDrafts is now async and throws on failure. The old pattern
  // (void callback) swallowed injection errors silently — the modal would close
  // even if no text was actually injected. Using await + try/catch lets us keep
  // the modal open and surface the error if injection fails.
  const handleInjectApproved = useCallback(async () => {
    try {
      await injectApprovedDrafts(reviewModal.approvedDrafts);
      reviewModal.closeModal();
      setStatus('ready');
    } catch (err) {
      // Don't close the modal — let the user see something went wrong
      console.error('[ScholarScope] Injection failed:', err);
      setErrorMessage('Could not inject into the page. Make sure the scholarship tab is still open.');
      setStatus('error');
    }
  }, [reviewModal]);

  const logout = useCallback(() => {
    chrome.storage.local.remove('auth_token');
    setIsAuthenticated(false);
  }, []);

  const clearDraft = useCallback(() => {
    chrome.storage.local.remove('draft');
    setFormData({
      title: '', link: '', description: '', eligibility: '',
      requirements: '', reward: '', start_date: '', end_date: '',
    });
    setStatus('ready');
    setErrorMessage('');
  }, []);

  const handleChange = useCallback((e) => {
    const { name, value } = e.target;
    setFormData(prev => {
      const updated = { ...prev, [name]: value };
      chrome.storage.local.set({ draft: updated });
      return updated;
    });
  }, []);

  const handleAutoExtract = useCallback(async () => {
    const token = await getToken();
    if (!token) { setStatus('error'); setErrorMessage('You are logged out.'); logout(); return; }

    setStatus('extracting');
    setExtractStep('Scanning page…');
    setErrorMessage('');

    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (!tabs[0]?.id) {
        setStatus('error'); setErrorMessage('No active tab found.'); return;
      }
      chrome.tabs.sendMessage(tabs[0].id, { action: 'DEEP_SCRAPE' }, async (response) => {
        if (chrome.runtime.lastError || !response) {
          setStatus('error');
          setErrorMessage('Cannot scan this page. Try refreshing.');
          return;
        }
        setExtractStep('Sending to AI…');
        try {
          const res = await api.post(
            '/submissions/',
            { title: response.title, url: response.url, raw_html: response.html },
            { headers: { Authorization: `Bearer ${token}` } }
          );
          if (res.status === 200 || res.status === 201) {
            setSavedId(res.data.id);
            chrome.storage.local.remove('draft');
            setStatus('success');
          }
        } catch (err) {
          const is401 = err.response?.status === 401;
          setStatus('error');
          setErrorMessage(
            is401 ? 'Session expired. Please log in again.'
                  : 'AI extraction failed. Try saving manually.'
          );
          if (is401) logout();
        }
      });
    });
  }, [logout]);

  const handleSave = useCallback(async () => {
    if (!formData.title?.trim()) {
      setStatus('error'); setErrorMessage('Title is required.'); return;
    }
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
      const is401 = err.response?.status === 401;
      setStatus('error');
      setErrorMessage(
        is401 ? 'Session expired. Please log in again.'
              : (err.response?.data?.detail || 'Save failed. Is the server running?')
      );
      if (is401) logout();
    }
  }, [formData, logout]);

  if (checkingAuth) return <CenterLoader />;
  if (!isAuthenticated) return <Login onLoginSuccess={() => setIsAuthenticated(true)} />;
  if (status === 'success') return <SuccessScreen onClose={() => window.close()} />;

  const isBusy = status === 'saving' || status === 'extracting';

  return (
    <div className="popup-root">

      <header className="popup-header">
        <div className="header-brand">
          <GraduationCap size={16} className="brand-icon" />
          <span className="brand-name">ScholarScope</span>
        </div>
        <div className="header-actions">
          <button onClick={clearDraft} className="icon-btn" title="Clear draft" disabled={isBusy}>
            <Trash2 size={14} />
          </button>
          <button onClick={logout} className="icon-btn" title="Sign out" disabled={isBusy}>
            <LogOut size={14} />
          </button>
        </div>
      </header>

      <div className="ai-section">
        <button onClick={handleAutoExtract} disabled={isBusy} className="ai-btn">
          {status === 'extracting'
            ? <><Loader2 size={16} className="spin" /><span>{extractStep}</span></>
            : <><Sparkles size={16} /><span>Auto-Extract with AI</span></>
          }
        </button>
        {status === 'extracting' && (
          <div className="progress-bar"><div className="progress-fill" /></div>
        )}
      </div>

      {/* Essay panel — now correctly imported as a named export */}
      <EssayDraftPanel
        status={essayStatus}
        step={essayStep}
        error={essayError}
        onDraft={handleAIEssayDrafting}
        onReset={resetEssay}
      />

      {/* Review modal — rendered at root so it overlays everything */}
      <ReviewModal
        isOpen={reviewModal.isOpen}
        drafts={reviewModal.drafts}
        approved={reviewModal.approved}
        allApproved={reviewModal.allApproved}
        onClose={reviewModal.closeModal}
        onUpdateDraft={reviewModal.updateDraft}
        onToggleApprove={reviewModal.toggleApprove}
        onApproveAll={reviewModal.approveAll}
        onInjectApproved={handleInjectApproved}
        getToken={getToken}
      />

      <div className="divider">
        <div className="divider-line" />
        <span className="divider-text">or enter manually</span>
        <div className="divider-line" />
      </div>

      {status === 'error' && (
        <div className="status-error">
          <AlertCircle size={14} />
          <span>{errorMessage}</span>
        </div>
      )}

      <div className="form-body">
        <Field label="Title" icon={BookOpen}>
          <input
            className="input" name="title" value={formData.title}
            onChange={handleChange} placeholder="Scholarship name"
          />
        </Field>

        <Field label="Page URL" icon={Link2}>
          <input
            className="input url-input" name="link" value={formData.link}
            readOnly title={formData.link}
          />
        </Field>

        <Field label="Reward / Amount" icon={DollarSign}>
          <input
            className="input" name="reward" value={formData.reward}
            onChange={handleChange} placeholder="e.g. $10,000 or Full Tuition"
          />
        </Field>

        <div className="two-col">
          <Field label="Eligibility" icon={Users}>
            <textarea
              className="input textarea" name="eligibility"
              value={formData.eligibility} onChange={handleChange}
              placeholder="Right-click selected text to add…"
            />
          </Field>
          <Field label="Requirements" icon={FileText}>
            <textarea
              className="input textarea" name="requirements"
              value={formData.requirements} onChange={handleChange}
              placeholder="Right-click selected text to add…"
            />
          </Field>
        </div>

        <button className="advanced-toggle" onClick={() => setShowAdvanced(v => !v)}>
          {showAdvanced ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          {showAdvanced ? 'Hide' : 'Show'} dates &amp; description
        </button>

        {showAdvanced && (
          <div className="advanced-fields">
            <div className="two-col">
              <Field label="Opens">
                <input type="date" className="input" name="start_date"
                  value={formData.start_date} onChange={handleChange} />
              </Field>
              <Field label="Deadline">
                <input type="date" className="input" name="end_date"
                  value={formData.end_date} onChange={handleChange} />
              </Field>
            </div>
            <Field label="Description">
              <textarea
                className="input textarea" name="description"
                value={formData.description} onChange={handleChange}
                placeholder="Brief overview…"
              />
            </Field>
          </div>
        )}
      </div>

      <footer className="popup-footer">
        <button onClick={handleSave} disabled={isBusy} className="save-btn">
          {status === 'saving'
            ? <><Loader2 size={16} className="spin" /> Saving…</>
            : <><Save size={16} /> Save to Dashboard</>
          }
        </button>
      </footer>

    </div>
  );
}

function CenterLoader() {
  return (
    <div style={{ display:'flex', justifyContent:'center', alignItems:'center', height:200 }}>
      <Loader2 size={24} className="spin" style={{ color:'#2563eb' }} />
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

// Wrap in error boundary so any future render crash shows a message
// instead of a blank white popup
export default function App() {
  return (
    <ErrorBoundary>
      <AppInner />
    </ErrorBoundary>
  );
}