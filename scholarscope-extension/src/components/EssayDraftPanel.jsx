// src/components/EssayDraftPanel.jsx
import { useCallback } from 'react';
import { Sparkles, Loader2, AlertCircle } from 'lucide-react';
import api from '../api';

// ── Polling ───────────────────────────────────────────────────────────────────
const pollForResults = async (jobId, token, onProgress, maxAttempts = 40) => {
  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    await new Promise(resolve => setTimeout(resolve, 2000));
    try {
      const res = await api.get(
        `/scholarships/draft_essays/status/${jobId}/`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (res.data.status === 'complete') return res.data;
      if (res.data.status === 'failed')   throw new Error('Job failed on server.');
      onProgress(`Drafting essays… (${attempt + 1}/${maxAttempts})`);
    } catch (err) {
      if (err.message === 'Job failed on server.') throw err;
      if (attempt === maxAttempts - 1) throw err;
      onProgress(`Checking status… (${attempt + 1}/${maxAttempts})`);
    }
  }
  throw new Error('Timed out. Your essays may still be processing — try again in a moment.');
};

// ── Chrome helpers ────────────────────────────────────────────────────────────
function getActiveTabId() {
  return new Promise((resolve, reject) => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (chrome.runtime.lastError) return reject(chrome.runtime.lastError);
      const tabId = tabs[0]?.id;
      if (!tabId) return reject(new Error('No active tab found.'));
      resolve(tabId);
    });
  });
}

function sendTabMessage(tabId, message) {
  return new Promise((resolve, reject) => {
    chrome.tabs.sendMessage(tabId, message, (response) => {
      if (chrome.runtime.lastError) return reject(chrome.runtime.lastError);
      resolve(response);
    });
  });
}

async function getPageMetadata() {
  try {
    const tabId = await getActiveTabId();
    const res   = await sendTabMessage(tabId, { action: 'SCRAPE_METADATA' });
    return { title: res?.title || '', url: res?.url || '' };
  } catch {
    return { title: '', url: '' };
  }
}

export async function injectApprovedDrafts(approvedDrafts) {
  const tabId = await getActiveTabId();
  return sendTabMessage(tabId, { action: 'INJECT_ESSAY_DRAFTS', drafts: approvedDrafts });
}

// ── Hook ──────────────────────────────────────────────────────────────────────
import { useState } from 'react';

export function useEssayDrafter({ getToken, reviewModal }) {
  const [essayStatus, setEssayStatus] = useState('idle');
  const [essayStep,   setEssayStep]   = useState('');
  const [essayError,  setEssayError]  = useState('');

  const handleAIEssayDrafting = useCallback(async (scholarshipId = null) => {
    const token = await getToken();
    if (!token) {
      setEssayStatus('error');
      setEssayError('You are not signed in.');
      return;
    }

    setEssayStatus('scanning');
    setEssayStep('Scanning for essay questions…');
    setEssayError('');

    let tabId;
    try {
      tabId = await getActiveTabId();
    } catch {
      setEssayStatus('error');
      setEssayError('Cannot access this tab.');
      return;
    }

    let rawPrompts;
    try {
      const readRes = await sendTabMessage(tabId, { action: 'EXTRACT_ESSAY_PROMPTS' });
      rawPrompts = readRes?.prompts || [];
    } catch {
      setEssayStatus('error');
      setEssayError('Could not read this page. Try refreshing.');
      return;
    }

    // Deduplicate
    const seen = new Set();
    const promptsToSend = rawPrompts
      .filter(p => {
        const key = p.prompt.trim().toLowerCase().slice(0, 100);
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      })
      .slice(0, 10);

    if (promptsToSend.length === 0) {
      setEssayStatus('error');
      setEssayError('No empty essay boxes found on this page.');
      return;
    }

    setEssayStatus('drafting');
    setEssayStep(`Found ${promptsToSend.length} question${promptsToSend.length > 1 ? 's' : ''}. Drafting with AI…`);

    const pageMetadata = await getPageMetadata();

    try {
      const startRes = await api.post(
        '/scholarships/draft_essays/',
        {
          prompts:        promptsToSend,
          scholarship_id: scholarshipId || null,
          page_metadata:  pageMetadata,
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      const jobId = startRes.data?.job_id;
      if (!jobId) throw new Error('Server did not return a job ID. Please try again.');

      setEssayStep('AI is drafting your essays…');

      const results  = await pollForResults(jobId, token, setEssayStep);
      const successful = (results.drafts || []).filter(d => d.confidence !== 'failed');

      if (successful.length === 0) {
        setEssayStatus('error');
        setEssayError('AI could not draft any essays. Try completing more of your profile.');
        return;
      }

      const merged = successful.map(draft => {
        const meta = promptsToSend.find(p => p.id === draft.id) || {};
        return { ...draft, prompt: meta.prompt || '', max_words: meta.max_words || 200 };
      });

      setEssayStatus('ready');
      reviewModal.openModal(merged, { hasContext: !!scholarshipId });

    } catch (err) {
      console.error('[ScholarScope] Essay drafting error:', err);
      setEssayStatus('error');
      setEssayError(err.response?.data?.error || err.message || 'AI drafting failed. Please try again.');
    }
  }, [getToken, reviewModal]);

  // Always draft immediately — no context prompt step
  const initiateDrafting = useCallback((savedScholarshipId) => {
    handleAIEssayDrafting(savedScholarshipId || null);
  }, [handleAIEssayDrafting]);

  const resetEssay = useCallback(() => {
    setEssayStatus('idle');
    setEssayStep('');
    setEssayError('');
    getActiveTabId()
      .then(tabId => sendTabMessage(tabId, { action: 'CLEAR_ESSAY_HIGHLIGHTS' }))
      .catch(() => {});
  }, []);

  return {
    essayStatus, essayStep, essayError,
    initiateDrafting, handleAIEssayDrafting, resetEssay,
    setEssayStatus,
  };
}

// ── EssayDraftPanel ───────────────────────────────────────────────────────────
export function EssayDraftPanel({
  status, step, error,
  savedScholarshipId,
  onInitiate,
  onReset,
}) {
  const isWorking = status === 'scanning' || status === 'drafting';

  return (
    <div className="essay-panel">
      <div className="essay-panel__header">
        <span className="essay-panel__label">
          <Sparkles size={12} />
          AI Essay Assistant
        </span>
      </div>

      {/* CTA button — shown when idle or after completion */}
      {(status === 'idle' || status === 'ready') && (
        <button
          className="essay-btn"
          onClick={() => onInitiate(savedScholarshipId)}
        >
          <Sparkles size={14} />
          {status === 'ready' ? 'Draft Again' : 'Draft Essay Responses'}
        </button>
      )}

      {/* Working state */}
      {isWorking && (
        <div className="essay-panel__progress">
          <Loader2 size={13} className="spin" />
          <span>{step || 'Working…'}</span>
        </div>
      )}

      {/* Error state */}
      {status === 'error' && (
        <div className="essay-panel__error">
          <AlertCircle size={13} />
          <span className="essay-panel__error-text">{error}</span>
          <button
            className="essay-panel__retry"
            onClick={() => { onReset?.(); onInitiate(savedScholarshipId); }}
          >
            Retry
          </button>
        </div>
      )}
    </div>
  );
}