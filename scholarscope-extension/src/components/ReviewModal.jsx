// src/components/ReviewModal.jsx
// ─────────────────────────────────────────────────────────────────────────────
// Human-in-the-Loop review interface for AI essay drafts.
// Shows all drafts before anything is injected into the page.
// Users can: Approve → inject, Edit inline, or Regenerate with instruction.
// ─────────────────────────────────────────────────────────────────────────────

import { useState, useCallback, useRef, useEffect } from 'react';
import {
  CheckCircle2, X, RefreshCw, ChevronDown, ChevronUp,
  Sparkles, Send, Loader2, Edit3, Check, AlertTriangle,
} from 'lucide-react';
import api from '../api';

// ── Constants ─────────────────────────────────────────────────────────────────

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

// ── Hook: useReviewModal ──────────────────────────────────────────────────────

export function useReviewModal() {
  const [isOpen, setIsOpen]   = useState(false);
  const [drafts, setDrafts]   = useState([]);   // [{id, prompt, draft, word_count, confidence, max_words}]
  const [approved, setApproved] = useState({});  // {id: boolean}

  const openModal = useCallback((incomingDrafts) => {
    // Merge prompt metadata from the content script with LLM draft results
    setDrafts(incomingDrafts);
    setApproved({});
    setIsOpen(true);
  }, []);

  const closeModal = useCallback(() => setIsOpen(false), []);

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
    isOpen, drafts, approved, approvedDrafts, allApproved,
    openModal, closeModal, updateDraft, toggleApprove, approveAll,
  };
}

// ── Main Component ────────────────────────────────────────────────────────────

// export default function ReviewModal({
//   isOpen,
//   drafts,
//   approved,
//   allApproved,
//   onClose,
//   onUpdateDraft,
//   onToggleApprove,
//   onApproveAll,
//   onInjectApproved,    // (approvedDrafts) => void
//   getToken,
// }) {
//   if (!isOpen) return null;

//   const approvedCount = Object.values(approved).filter(Boolean).length;

//   return (
//     <div className="rm-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
//       <div className="rm-panel">

//         {/* ── Header ─────────────────────────────────────────────────────── */}
//         <div className="rm-header">
//           <div className="rm-header-left">
//             <Sparkles size={16} className="rm-header-icon" />
//             <div>
//               <h2 className="rm-title">Review AI Drafts</h2>
//               <p className="rm-subtitle">
//                 {drafts.length} essay{drafts.length !== 1 ? 's' : ''} drafted
//                 · approve before injecting
//               </p>
//             </div>
//           </div>
//           <button className="rm-close" onClick={onClose}>
//             <X size={16} />
//           </button>
//         </div>

//         {/* ── Safety notice ───────────────────────────────────────────────── */}
//         <div className="rm-safety-notice">
//           <AlertTriangle size={12} />
//           <span>
//             AI drafts require your review. Edit freely — nothing is submitted until <em>you</em> decide.
//           </span>
//         </div>

//         {/* ── Draft cards ─────────────────────────────────────────────────── */}
//         <div className="rm-scroll">
//           {drafts.map((draft, index) => (
//             <DraftCard
//               key={draft.id}
//               draft={draft}
//               index={index}
//               isApproved={!!approved[draft.id]}
//               onToggleApprove={() => onToggleApprove(draft.id)}
//               onUpdateDraft={(text) => onUpdateDraft(draft.id, text)}
//               getToken={getToken}
//             />
//           ))}
//         </div>

//         {/* ── Footer actions ───────────────────────────────────────────────── */}
//         <div className="rm-footer">
//           {!allApproved && (
//             <button className="rm-approve-all-btn" onClick={onApproveAll}>
//               <Check size={13} />
//               Approve All
//             </button>
//           )}
//           <button
//             className={`rm-inject-btn ${approvedCount === 0 ? 'rm-inject-btn--disabled' : ''}`}
//             onClick={() => approvedCount > 0 && onInjectApproved()}
//             disabled={approvedCount === 0}
//           >
//             <Send size={13} />
//             Inject {approvedCount > 0 ? `${approvedCount} Approved` : 'Selected'}
//           </button>
//         </div>

//       </div>
//     </div>
//   );
// }

export default function ReviewModal({
  isOpen, drafts, approved, allApproved, onClose, 
  onUpdateDraft, onToggleApprove, onApproveAll, onInjectApproved, getToken,
}) {
  if (!isOpen) return null;

  const approvedCount = Object.values(approved).filter(Boolean).length;

  return (
    /* We remove the background click-to-close here because this view 
       now occupies the entire extension popup width/height */
    <div className="rm-view-container">
      <div className="rm-panel">
        
        {/* Header stays pinned */}
        <div className="rm-header">
          <div className="rm-header-left">
            <Sparkles size={16} className="rm-header-icon" />
            <div>
              <h2 className="rm-title">Review Drafts</h2>
              <p className="rm-subtitle">{drafts.length} essays found</p>
            </div>
          </div>
          <button className="rm-close" onClick={onClose} title="Back to scan">
            <X size={16} />
          </button>
        </div>

        {/* Scrollable Area */}
        <div className="rm-scroll">
          <div className="rm-safety-notice">
            <AlertTriangle size={12} />
            <span>Review and edit before injecting.</span>
          </div>

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

        {/* Footer stays pinned at bottom */}
        <div className="rm-footer">
          <button className="rm-approve-all-btn" onClick={onApproveAll}>
            {allApproved ? <Check size={14}/> : <CheckCircle2 size={14}/>}
            {allApproved ? 'All Ready' : 'Approve All'}
          </button>
          
          <button
            className={`rm-inject-btn ${approvedCount === 0 ? 'rm-inject-btn--disabled' : ''}`}
            onClick={() => approvedCount > 0 && onInjectApproved()}
            disabled={approvedCount === 0}
          >
            <Send size={14} />
            Inject ({approvedCount})
          </button>
        </div>
      </div>
    </div>
  );
}

// ── DraftCard ─────────────────────────────────────────────────────────────────

function DraftCard({ draft, index, isApproved, onToggleApprove, onUpdateDraft, getToken }) {
  const [isEditing,      setIsEditing]      = useState(false);
  const [editText,       setEditText]       = useState(draft.draft);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [instruction,    setInstruction]    = useState('');
  const [showRegen,      setShowRegen]      = useState(false);
  const [regenError,     setRegenError]     = useState('');
  const [showPrompt,     setShowPrompt]     = useState(false);
  const textareaRef = useRef(null);

  // Keep local editText in sync when parent updates the draft (e.g. after regen)
  useEffect(() => { setEditText(draft.draft); }, [draft.draft]);

  // Auto-resize textarea
  useEffect(() => {
    if (isEditing && textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = textareaRef.current.scrollHeight + 'px';
    }
  }, [isEditing, editText]);

  const handleSaveEdit = () => {
    onUpdateDraft(editText);
    setIsEditing(false);
  };

  const handleCancelEdit = () => {
    setEditText(draft.draft);
    setIsEditing(false);
  };

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

  const conf = CONFIDENCE_META[draft.confidence] || CONFIDENCE_META.medium;
  const wordCount = editText.trim().split(/\s+/).filter(Boolean).length;
  const overLimit = draft.max_words && wordCount > draft.max_words;

  return (
    <div className={`rm-card ${isApproved ? 'rm-card--approved' : ''}`}>

      {/* Card header */}
      <div className="rm-card-header">
        <div className="rm-card-meta">
          <span className="rm-card-index">Essay {index + 1}</span>
          <span
            className="rm-card-confidence"
            style={{ color: conf.color, borderColor: conf.color + '40', background: conf.color + '14' }}
          >
            {conf.label} confidence
          </span>
          <span className={`rm-card-wordcount ${overLimit ? 'rm-card-wordcount--over' : ''}`}>
            {wordCount}{draft.max_words ? `/${draft.max_words}` : ''} words
          </span>
        </div>

        {/* Approve toggle */}
        <button
          className={`rm-approve-btn ${isApproved ? 'rm-approve-btn--on' : ''}`}
          onClick={onToggleApprove}
        >
          <CheckCircle2 size={14} />
          {isApproved ? 'Approved' : 'Approve'}
        </button>
      </div>

      {/* Collapsible prompt */}
      <button className="rm-prompt-toggle" onClick={() => setShowPrompt(v => !v)}>
        <span className="rm-prompt-label">Question</span>
        {showPrompt ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
      </button>
      {showPrompt && draft.prompt && (
        <p className="rm-prompt-text">{draft.prompt}</p>
      )}
      {/* Draft text / editor */}
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
            <button className="rm-edit-save" onClick={handleSaveEdit}>
              <Check size={12} /> Save
            </button>
          </div>
        </div>
      ) : (
        <div className="rm-draft-text" onClick={() => setIsEditing(true)}>
          {draft.draft || <span className="rm-draft-empty">Draft unavailable.</span>}
        </div>
      )}

      {/* Action row */}
      {!isEditing && (
        <div className="rm-card-actions">
          <button className="rm-action-btn" onClick={() => setIsEditing(true)}>
            <Edit3 size={11} /> Edit
          </button>
          <button
            className={`rm-action-btn ${showRegen ? 'rm-action-btn--active' : ''}`}
            onClick={() => setShowRegen(v => !v)}
          >
            <RefreshCw size={11} /> Regenerate
          </button>
        </div>
      )}

      {/* Regenerate panel */}
      {showRegen && !isEditing && (
        <div className="rm-regen-panel">
          {/* Quick instruction chips */}
          <div className="rm-chips">
            {QUICK_INSTRUCTIONS.map(qi => (
              <button
                key={qi}
                className={`rm-chip ${instruction === qi ? 'rm-chip--active' : ''}`}
                onClick={() => setInstruction(qi)}
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
                ? <Loader2 size={13} className="spin" />
                : <Send size={13} />
              }
            </button>
          </div>

          {regenError && (
            <p className="rm-regen-error">{regenError}</p>
          )}
        </div>
      )}

    </div>
  );
}