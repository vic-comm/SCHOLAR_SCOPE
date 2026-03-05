// src/App.jsx
import { useState, useEffect, useCallback, Component } from 'react';
import {
  Save, Trash2, Loader2, CheckCircle, LogOut,
  Sparkles, ChevronDown, ChevronUp, AlertCircle, Info,
  GraduationCap, Link2, DollarSign, Users, FileText, BookOpen
} from 'lucide-react';
import Login from './Login.jsx';
import api from './api';
import ReviewModal, { useReviewModal } from './components/ReviewModal';
import {
  useEssayDrafter,
  injectApprovedDrafts,
  EssayDraftPanel,
} from './components/EssayDraftPanel';
import './components/ReviewModal.css';

// ── Error boundary ─────────────────────────────────────────────────────────────
class ErrorBoundary extends Component {
  constructor(props) { super(props); this.state = { error: null }; }
  static getDerivedStateFromError(error) { return { error }; }
  componentDidCatch(error, info) {
    console.error('[ScholarScope] Render crash:', error, info.componentStack);
  }
  render() {
    if (this.state.error) {
      return (
        <div style={{ padding:'18px 16px', fontFamily:'system-ui', background:'#fff', color:'#1a1814', minHeight:200 }}>
          <p style={{ color:'#dc2626', fontWeight:600, marginBottom:6, fontSize:13 }}>Something went wrong</p>
          <p style={{ color:'#5a5650', fontSize:11, marginBottom:14, wordBreak:'break-word' }}>{this.state.error.message}</p>
          <button
            onClick={() => this.setState({ error: null })}
            style={{ background:'#2248d4', color:'#fff', border:'none', borderRadius:6, padding:'6px 14px', fontSize:12, cursor:'pointer' }}
          >
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

const getToken = () =>
  new Promise(resolve =>
    chrome.storage.local.get(['auth_token'], r => resolve(r.auth_token || null))
  );

const Field = ({ label, icon: Icon, children }) => (
  <div className="field-group">
    <label className="field-label">
      {Icon && <Icon className="field-icon" size={11} />}
      {label}
    </label>
    {children}
  </div>
);

// ── Helper — does the extracted data have anything useful? ─────────────────────
function isExtractedDataMeaningful(data) {
  if (!data) return false;
  const fields = [
    data.title, data.description, data.eligibility,
    data.requirements, data.reward, data.deadline,
  ];
  // At least 2 non-trivial fields must be present
  const nonEmpty = fields.filter(f => {
    if (!f) return false;
    if (Array.isArray(f)) return f.length > 0;
    return String(f).trim().length > 5;
  });
  return nonEmpty.length >= 2;
}

function AppInner() {
  const [isAuthenticated,    setIsAuthenticated]    = useState(false);
  const [checkingAuth,       setCheckingAuth]       = useState(true);
  const [status,             setStatus]             = useState('ready');
  const [errorMessage,       setErrorMessage]       = useState('');
  const [extractStep,        setExtractStep]        = useState('');
  const [showAdvanced,       setShowAdvanced]       = useState(false);
  const [savedScholarshipId, setSavedScholarshipId] = useState(null);
  // 'none' | 'sparse' | null — tracks what auto-extract found
  const [extractNotice,      setExtractNotice]      = useState(null);

  const reviewModal = useReviewModal();
  const {
    essayStatus, essayStep, essayError,
    initiateDrafting, resetEssay,
  } = useEssayDrafter({ getToken, reviewModal });

  const [formData, setFormData] = useState({
    title: '', link: '', description: '',
    eligibility: '', requirements: '', reward: '',
    start_date: '', end_date: '',
  });

  useEffect(() => {
    chrome.storage.local.get(['auth_token'], (r) => {
      setIsAuthenticated(!!r.auth_token);
      setCheckingAuth(false);
    });
  }, []);

  useEffect(() => {
    const handler = (changes) => {
      if (changes.draft?.newValue) {
        setFormData(prev => ({ ...prev, ...changes.draft.newValue }));
      }
    };
    chrome.storage.onChanged.addListener(handler);
    return () => chrome.storage.onChanged.removeListener(handler);
  }, []);

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

  useEffect(() => {
    const checkSaved = async () => {
      const token = await getToken();
      if (!token) { setSavedScholarshipId(false); return; }
      chrome.tabs.query({ active: true, currentWindow: true }, async (tabs) => {
        const tab = tabs[0];
        if (!tab?.url) { setSavedScholarshipId(false); return; }
        let pageTitle = tab.title || '';
        try {
          const meta = await new Promise((resolve, reject) => {
            chrome.tabs.sendMessage(tab.id, { action: 'SCRAPE_METADATA' }, (res) => {
              if (chrome.runtime.lastError) return reject(chrome.runtime.lastError);
              resolve(res);
            });
          });
          pageTitle = meta?.title || pageTitle;
        } catch { /* use tab.title */ }
        try {
          const res = await api.get('/scholarships/check/', {
            params: { title: pageTitle, url: tab.url },
            headers: { Authorization: `Bearer ${token}` },
          });
          setSavedScholarshipId(res.data.matched && res.data.id ? res.data.id : false);
        } catch {
          setSavedScholarshipId(false);
        }
      });
    };
    checkSaved();
  }, []);

  const handleInjectApproved = useCallback(async () => {
    try {
      await injectApprovedDrafts(reviewModal.approvedDrafts);
      reviewModal.closeModal();
      setStatus('ready');
    } catch (err) {
      console.error('[ScholarScope] Injection failed:', err);
      setErrorMessage('Could not inject into the page. Make sure the scholarship tab is still open.');
      setStatus('error');
    }
  }, [reviewModal]);

  const handleSaveFromModal = useCallback(() => {
    reviewModal.closeModal();
    setTimeout(() => {
      setStatus('ready');
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }, 200);
  }, [reviewModal]);

  const logout = useCallback(() => {
    chrome.storage.local.remove('auth_token');
    setIsAuthenticated(false);
  }, []);

  const clearDraft = useCallback(() => {
    chrome.storage.local.remove('draft');
    setFormData({ title:'', link:'', description:'', eligibility:'', requirements:'', reward:'', start_date:'', end_date:'' });
    setStatus('ready');
    setErrorMessage('');
    setExtractNotice(null);
  }, []);

  const handleChange = useCallback((e) => {
    const { name, value } = e.target;
    setFormData(prev => {
      const updated = { ...prev, [name]: value };
      chrome.storage.local.set({ draft: updated });
      return updated;
    });
  }, []);

  // ── Poll /submissions/<id>/status/ until the Celery task settles ────────────
  const pollSubmissionStatus = useCallback(async (submissionId, token, maxAttempts = 20) => {
    for (let i = 0; i < maxAttempts; i++) {
      await new Promise(r => setTimeout(r, 2000));
      setExtractStep(`Processing… (${i + 1}/${maxAttempts})`);
      try {
        const res = await api.get(
          `/submissions/${submissionId}/submission_status/`,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        const { submission_status, data_quality, scholarship_id, sparse_fields = [] } = res.data;

        if (submission_status === 'processing') continue; // still running

        if (submission_status === 'rejected' || data_quality === 'none') {
          // QualityCheck or AI said this isn't a scholarship page
          setStatus('ready');
          setExtractNotice('none');
          return;
        }

        if (submission_status === 'approved') {
          if (scholarship_id) setSavedScholarshipId(scholarship_id);
          if (data_quality === 'sparse') {
            // Saved but key fields are missing — stay on form, show notice
            setStatus('ready');
            setExtractNotice({ type: 'sparse', fields: sparse_fields });
            return;
          }
          // Full quality — go to success screen
          chrome.storage.local.remove('draft');
          setStatus('success');
          return;
        }
      } catch {
        // Transient error — keep polling
      }
    }
    // Timed out — task may still complete in background
    setStatus('error');
    setErrorMessage('Processing is taking longer than expected. Check your dashboard in a moment.');
  }, [logout]);

  const handleAutoExtract = useCallback(async () => {
    const token = await getToken();
    if (!token) { setStatus('error'); setErrorMessage('You are logged out.'); logout(); return; }

    setStatus('extracting');
    setExtractStep('Scanning page…');
    setErrorMessage('');
    setExtractNotice(null);

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
            '/submissions/',
            { title: response.title, url: response.url, raw_html: response.html },
            { headers: { Authorization: `Bearer ${token}` } }
          );

          if (res.status === 200 || res.status === 201) {
            const { id, submission_id, data_quality, sparse_fields = [] } = res.data;

            // ── Fast path: scholarship was already in DB, settled immediately ─
            if (data_quality === 'full') {
              if (id) setSavedScholarshipId(id);
              chrome.storage.local.remove('draft');
              setStatus('success');
              return;
            }

            if (data_quality === 'sparse') {
              if (id) setSavedScholarshipId(id);
              setStatus('ready');
              setExtractNotice({ type: 'sparse', fields: sparse_fields });
              return;
            }

            // ── Async path: task was queued, poll for result ───────────────
            if (data_quality === 'processing' && submission_id) {
              setExtractStep('AI is analysing the page…');
              await pollSubmissionStatus(submission_id, token);
              return;
            }

            // Fallback
            setStatus('ready');
          }
        } catch (err) {
          const is401 = err.response?.status === 401;
          setStatus('error');
          setErrorMessage(
            is401
              ? 'Session expired. Please log in again.'
              : 'AI extraction failed. Try saving manually.'
          );
          if (is401) logout();
        }
      });
    });
  }, [logout, pollSubmissionStatus]);

  const handleSave = useCallback(async () => {
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
        setSavedScholarshipId(res.data.id);
        chrome.storage.local.remove('draft');
        setStatus('success');
      }
    } catch (err) {
      const is401 = err.response?.status === 401;
      setStatus('error');
      setErrorMessage(
        is401
          ? 'Session expired. Please log in again.'
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

      {/* ── Auto-extract section ── */}
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

      {/* ── Extract notices — driven by data_quality from backend ── */}
      {extractNotice === 'none' && (
        <div className="extract-notice extract-notice--warn">
          <Info size={13} />
          <div>
            <p className="extract-notice__title">This page doesn't look like a scholarship listing</p>
            <p className="extract-notice__sub">
              Navigate to the scholarship's detail or application page and try again,
              or fill in the form below manually.
            </p>
          </div>
          <button className="extract-notice__dismiss" onClick={() => setExtractNotice(null)}>✕</button>
        </div>
      )}
      {extractNotice?.type === 'sparse' && (
        <div className="extract-notice extract-notice--info">
          <Info size={13} />
          <div>
            <p className="extract-notice__title">Saved — but some fields are missing</p>
            <p className="extract-notice__sub">
              {extractNotice.fields?.length > 0
                ? `Couldn't find: ${extractNotice.fields.join(', ')}. Fill these in below for better essay drafts.`
                : 'Check the form below and add any missing details before saving.'
              }
            </p>
          </div>
          <button className="extract-notice__dismiss" onClick={() => setExtractNotice(null)}>✕</button>
        </div>
      )}

      {/* ── Essay panel ── */}
      <EssayDraftPanel
        status={essayStatus}
        step={essayStep}
        error={essayError}
        savedScholarshipId={savedScholarshipId}
        onInitiate={initiateDrafting}
        onReset={resetEssay}
      />

      {/* ── Review modal ── */}
      <ReviewModal
        isOpen={reviewModal.isOpen}
        drafts={reviewModal.drafts}
        approved={reviewModal.approved}
        allApproved={reviewModal.allApproved}
        draftMeta={reviewModal.draftMeta}
        onClose={reviewModal.closeModal}
        onUpdateDraft={reviewModal.updateDraft}
        onToggleApprove={reviewModal.toggleApprove}
        onApproveAll={reviewModal.approveAll}
        onInjectApproved={handleInjectApproved}
        onSaveScholarship={handleSaveFromModal}
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
            <textarea className="input textarea" name="eligibility" value={formData.eligibility} onChange={handleChange}
              placeholder="Right-click selected text to add…" />
          </Field>
          <Field label="Requirements" icon={FileText}>
            <textarea className="input textarea" name="requirements" value={formData.requirements} onChange={handleChange}
              placeholder="Right-click selected text to add…" />
          </Field>
        </div>

        <button
          className={`advanced-toggle${showAdvanced ? ' advanced-toggle--open' : ''}`}
          onClick={() => setShowAdvanced(v => !v)}
        >
          {showAdvanced ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
          {showAdvanced ? 'Hide' : 'Show'} dates &amp; description
        </button>

        {showAdvanced && (
          <div className="advanced-fields">
            <div className="two-col">
              <Field label="Opens">
                <input type="date" className="input" name="start_date" value={formData.start_date} onChange={handleChange} />
              </Field>
              <Field label="Deadline">
                <input type="date" className="input" name="end_date" value={formData.end_date} onChange={handleChange} />
              </Field>
            </div>
            <Field label="Description">
              <textarea className="input textarea" name="description" value={formData.description} onChange={handleChange} placeholder="Brief overview…" />
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
    <div style={{ display:'flex', justifyContent:'center', alignItems:'center', height:480, background:'#f5f4f0' }}>
      <Loader2 size={24} className="spin" style={{ color:'#2248d4' }} />
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

export default function App() {
  return (
    <ErrorBoundary>
      <AppInner />
    </ErrorBoundary>
  );
}