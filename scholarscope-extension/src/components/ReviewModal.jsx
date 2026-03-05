// src/components/ReviewModal.jsx
import { useState, useCallback, useRef, useEffect } from 'react';
import {
  CheckCircle2, ChevronLeft, RefreshCw, ChevronDown, ChevronUp,
  Sparkles, Send, Loader2, Edit3, Check, AlertTriangle, Info,
} from 'lucide-react';
import api from '../api';

const QUICK_INSTRUCTIONS = [
  'Make this more enthusiastic',
  'Make this more formal',
  'Shorten to fit the word limit',
  'Add more specific examples',
  'Make this more personal',
  'Focus more on technical skills',
];

const CONFIDENCE_META = {
  high:   { label: 'High',   color: '#10b981' },
  medium: { label: 'Medium', color: '#f59e0b' },
  low:    { label: 'Low',    color: '#f87171' },
  failed: { label: 'Failed', color: '#f87171' },
};

// ── Hook ──────────────────────────────────────────────────────────────────────
export function useReviewModal() {
  const [isOpen,    setIsOpen]    = useState(false);
  const [drafts,    setDrafts]    = useState([]);
  const [approved,  setApproved]  = useState({});
  const [draftMeta, setDraftMeta] = useState(null);

  const openModal = useCallback((incomingDrafts, meta = null) => {
    setDrafts(incomingDrafts);
    setApproved({});
    setDraftMeta(meta);
    setIsOpen(true);
  }, []);

  const closeModal = useCallback(() => {
    setIsOpen(false);
    setDraftMeta(null);
  }, []);

  const updateDraft = useCallback((id, newText) => {
    setDrafts(prev =>
      prev.map(d => d.id === id
        ? { ...d, draft: newText, word_count: newText.trim().split(/\s+/).length }
        : d
      )
    );
  }, []);

  const toggleApprove = useCallback((id) => {
    setApproved(prev => ({ ...prev, [id]: !prev[id] }));
  }, []);

  const approveAll = useCallback(() => {
    const all = {};
    drafts.forEach(d => { all[d.id] = true; });
    setApproved(all);
  }, [drafts]);

  const approvedDrafts = drafts.filter(d => approved[d.id]);
  const allApproved    = drafts.length > 0 && approvedDrafts.length === drafts.length;

  return {
    isOpen, drafts, approved, approvedDrafts, allApproved, draftMeta,
    openModal, closeModal, updateDraft, toggleApprove, approveAll,
  };
}

// ── ReviewModal ───────────────────────────────────────────────────────────────
export default function ReviewModal({
  isOpen, drafts, approved, allApproved, draftMeta,
  onClose, onUpdateDraft, onToggleApprove, onApproveAll,
  onInjectApproved, onSaveScholarship, getToken,
}) {
  if (!isOpen) return null;

  const approvedCount  = Object.values(approved).filter(Boolean).length;
  const withoutContext = draftMeta && !draftMeta.hasContext;

  return (
    <div className="rm-view-container">
      <div className="rm-panel">

        {/* Header */}
        <div className="rm-header">
          <button className="rm-back-btn" onClick={onClose}>
            <ChevronLeft size={13} />
            Back
          </button>
          <div className="rm-header-left">
            <Sparkles size={14} className="rm-header-icon" />
            <div>
              <h2 className="rm-title">Review Drafts</h2>
              <p className="rm-subtitle">
                {drafts.length} essay{drafts.length !== 1 ? 's' : ''} · approve before injecting
              </p>
            </div>
          </div>
        </div>

        {/* Scroll area — contains everything between header and footer */}
        <div className="rm-scroll">

          <div className="rm-safety-notice">
            <AlertTriangle size={11} />
            <span>Review carefully — nothing is submitted until <em>you</em> approve and inject.</span>
          </div>

          {withoutContext && (
            <div className="rm-context-warning">
              <div className="rm-context-warning__body">
                <Info size={12} className="rm-context-warning__icon" />
                <div>
                  <p className="rm-context-warning__title">Drafted without scholarship context</p>
                  <p className="rm-context-warning__sub">
                    Save this scholarship first so the AI knows who it's for and what it values.
                  </p>
                </div>
              </div>
              <button className="rm-context-warning__cta" onClick={onSaveScholarship}>
                Save scholarship &amp; regenerate
              </button>
            </div>
          )}

          {drafts.map((draft, index) => (
            <DraftCard
              key={draft.id}
              draft={draft}
              index={index}
              isApproved={!!approved[draft.id]}
              onToggleApprove={() => onToggleApprove(draft.id)}
              onUpdateDraft={(text) => onUpdateDraft(draft.id, text)}
              getToken={getToken}
            />
          ))}

        </div>

        {/* Footer */}
        <div className="rm-footer">
          <button className="rm-approve-all-btn" onClick={onApproveAll}>
            {allApproved ? <Check size={13} /> : <CheckCircle2 size={13} />}
            {allApproved ? 'All Ready' : 'Approve All'}
          </button>
          <button
            className="rm-inject-btn"
            onClick={() => approvedCount > 0 && onInjectApproved()}
            disabled={approvedCount === 0}
          >
            <Send size={13} />
            Inject ({approvedCount})
          </button>
        </div>

      </div>
    </div>
  );
}

// ── DraftCard — always expanded, no collapse logic ────────────────────────────
function DraftCard({ draft, index, isApproved, onToggleApprove, onUpdateDraft, getToken }) {
  const [isEditing,      setIsEditing]      = useState(false);
  const [editText,       setEditText]       = useState(draft.draft || '');
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [instruction,    setInstruction]    = useState('');
  const [showRegen,      setShowRegen]      = useState(false);
  const [regenError,     setRegenError]     = useState('');
  const [showPrompt,     setShowPrompt]     = useState(false);
  const textareaRef = useRef(null);

  // Keep editText in sync if parent updates the draft (e.g. after regeneration)
  useEffect(() => {
    setEditText(draft.draft || '');
  }, [draft.draft]);

  // Auto-resize textarea while editing
  useEffect(() => {
    if (isEditing && textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = textareaRef.current.scrollHeight + 'px';
    }
  }, [isEditing, editText]);

  const handleSaveEdit   = () => { onUpdateDraft(editText); setIsEditing(false); };
  const handleCancelEdit = () => { setEditText(draft.draft || ''); setIsEditing(false); };

  const handleRegenerate = async () => {
    if (!instruction.trim()) return;
    setIsRegenerating(true);
    setRegenError('');
    try {
      const token = await getToken();
      const res = await api.post(
        '/scholarships/regenerate_essay/',
        {
          prompt:        draft.prompt,
          current_draft: draft.draft,
          instruction:   instruction.trim(),
          max_words:     draft.max_words || 200,
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      onUpdateDraft(res.data.draft);
      setInstruction('');
      setShowRegen(false);
    } catch (err) {
      setRegenError(err.response?.data?.error || 'Regeneration failed. Try again.');
    } finally {
      setIsRegenerating(false);
    }
  };

  const conf      = CONFIDENCE_META[draft.confidence] || CONFIDENCE_META.medium;
  const text      = isEditing ? editText : (draft.draft || '');
  const wordCount = text.trim().split(/\s+/).filter(Boolean).length;
  const overLimit = draft.max_words && wordCount > draft.max_words;

  return (
    <div className={`rm-card${isApproved ? ' rm-card--approved' : ''}`}>

      {/* ── Card header ── */}
      <div className="rm-card-header">
        <div className="rm-card-meta">
          <span className="rm-card-index">Essay {index + 1}</span>
          <span
            className="rm-card-confidence"
            style={{
              color:       conf.color,
              borderColor: conf.color + '55',
              background:  conf.color + '18',
            }}
          >
            {conf.label}
          </span>
          <span className={`rm-card-wordcount${overLimit ? ' rm-card-wordcount--over' : ''}`}>
            {wordCount}{draft.max_words ? `/${draft.max_words}w` : 'w'}
          </span>
        </div>
        <button
          className={`rm-approve-btn${isApproved ? ' rm-approve-btn--on' : ''}`}
          onClick={onToggleApprove}
        >
          <CheckCircle2 size={12} />
          {isApproved ? 'Approved' : 'Approve'}
        </button>
      </div>

      {/* ── Question (collapsible) ── */}
      {draft.prompt && (
        <>
          <button className="rm-prompt-toggle" onClick={() => setShowPrompt(v => !v)}>
            <span className="rm-prompt-label">Question</span>
            {showPrompt ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
          </button>
          {showPrompt && (
            <p className="rm-prompt-text">{draft.prompt}</p>
          )}
        </>
      )}

      {/* ── Draft body ── */}
      {isEditing ? (
        <div className="rm-edit-area">
          <textarea
            ref={textareaRef}
            className="rm-edit-textarea"
            value={editText}
            onChange={e => setEditText(e.target.value)}
            autoFocus
          />
          <div className="rm-edit-actions">
            <button className="rm-edit-cancel" onClick={handleCancelEdit}>Cancel</button>
            <button className="rm-edit-save"   onClick={handleSaveEdit}>
              <Check size={11} /> Save
            </button>
          </div>
        </div>
      ) : (
        /* Full draft text — NO max-height, NO overflow, NO mask */
        <div className="rm-draft-text" onClick={() => setIsEditing(true)}>
          {draft.draft
            ? draft.draft
            : <span className="rm-draft-empty">No draft generated.</span>
          }
        </div>
      )}

      {/* ── Action row ── */}
      {!isEditing && (
        <div className="rm-card-actions">
          <button className="rm-action-btn" onClick={() => setIsEditing(true)}>
            <Edit3 size={11} /> Edit
          </button>
          <button
            className={`rm-action-btn rm-action-btn--regen${showRegen ? ' rm-action-btn--active' : ''}`}
            onClick={() => { setShowRegen(v => !v); setRegenError(''); }}
          >
            <RefreshCw size={11} />
            {showRegen ? 'Close' : 'Regenerate'}
          </button>
        </div>
      )}

      {/* ── Regen panel ── */}
      {showRegen && !isEditing && (
        <div className="rm-regen-panel">
          <div className="rm-chips">
            {QUICK_INSTRUCTIONS.map(qi => (
              <button
                key={qi}
                className={`rm-chip${instruction === qi ? ' rm-chip--active' : ''}`}
                onClick={() => setInstruction(prev => prev === qi ? '' : qi)}
              >
                {qi}
              </button>
            ))}
          </div>
          <div className="rm-regen-input-row">
            <input
              className="rm-regen-input"
              placeholder="Or type a custom instruction…"
              value={instruction}
              onChange={e => setInstruction(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && !isRegenerating && handleRegenerate()}
            />
            <button
              className="rm-regen-send"
              onClick={handleRegenerate}
              disabled={!instruction.trim() || isRegenerating}
            >
              {isRegenerating
                ? <><Loader2 size={11} className="spin" /> Rewriting…</>
                : <><RefreshCw size={11} /> Regenerate</>
              }
            </button>
          </div>
          {regenError && <p className="rm-regen-error">{regenError}</p>}
        </div>
      )}

    </div>
  );
}