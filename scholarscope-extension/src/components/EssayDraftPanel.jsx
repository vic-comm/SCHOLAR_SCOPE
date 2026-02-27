// // src/components/EssayDraftPanel.jsx
// import { useState, useCallback } from 'react';
// import { Sparkles, Loader2, AlertCircle } from 'lucide-react';
// import api from '../api';

// // ── Bug 1: pollForResults was defined INSIDE the hook body but OUTSIDE
// // useCallback, meaning it got re-created on every render and couldn't
// // be properly referenced. Move it outside the hook entirely. ──────────────────

// const pollForResults = async (jobId, token, onProgress, maxAttempts = 40) => {
//   for (let attempt = 0; attempt < maxAttempts; attempt++) {
//     await new Promise(resolve => setTimeout(resolve, 2000));

//     try {
//       const res = await api.get(
//         `/scholarships/draft_essays/status/${jobId}/`,
//         { headers: { Authorization: `Bearer ${token}` } }
//       );

//       if (res.data.status === 'complete') return res.data;
//       if (res.data.status === 'failed')   throw new Error('Job failed on server.');

//       onProgress(`Drafting essays… (${attempt + 1}/${maxAttempts})`);

//     } catch (err) {
//       // Network error during polling — don't give up immediately,
//       // only bail on a real server-side failure or final attempt
//       if (err.message === 'Job failed on server.') throw err;
//       if (attempt === maxAttempts - 1) throw err;
//       onProgress(`Checking status… (${attempt + 1}/${maxAttempts})`);
//     }
//   }
//   throw new Error('Timed out. Your essays may still be processing — try again in a moment.');
// };


// export function useEssayDrafter({ getToken, reviewModal }) {
//   const [essayStatus, setEssayStatus] = useState('idle');
//   const [essayStep,   setEssayStep]   = useState('');
//   const [essayError,  setEssayError]  = useState('');

//   const handleAIEssayDrafting = useCallback(async () => {
//     const token = await getToken();
//     if (!token) {
//       setEssayStatus('error');
//       setEssayError('You are not signed in.');
//       return;
//     }

//     setEssayStatus('scanning');
//     setEssayStep('Scanning for essay questions…');
//     setEssayError('');

//     // ── Bug 2: The original nested an async callback inside chrome.tabs.query
//     // inside chrome.tabs.sendMessage — deeply nested callbacks where try/catch
//     // doesn't cross boundaries. Any throw inside the inner callback was silently
//     // swallowed, making errors invisible.
//     //
//     // Fix: wrap all chrome callbacks in Promises so the entire flow is a flat
//     // async/await chain with a single try/catch at the top. ──────────────────

//     let tabId;
//     try {
//       tabId = await getActiveTabId();
//     } catch {
//       setEssayStatus('error');
//       setEssayError('Cannot access this tab.');
//       return;
//     }

// let rawPrompts;
// try {
//   const readRes = await sendTabMessage(tabId, { action: 'EXTRACT_ESSAY_PROMPTS' });
//   rawPrompts = readRes?.prompts || [];
// } catch (err) {
//   setEssayStatus('error');
//   setEssayError('Could not read this page. Try refreshing.');
//   return;
// }

// // 1. Deduplicate by prompt text (exact same question detected multiple times)
//     const seen = new Set();
//     const uniquePrompts = rawPrompts.filter(p => {
//     const key = p.prompt.trim().toLowerCase().slice(0, 100); // Increased slice for better accuracy
//     if (seen.has(key)) return false;
//     seen.add(key);
//     return true;
//     });

//     // 2. Hard cap for the Fellowship demo (don't overwhelm Ollama/Gemini)
//     const capped = uniquePrompts.slice(0, 10);

//     if (capped.length === 0) {
//     setEssayStatus('error');
//     setEssayError('No empty essay boxes found on this page.');
//     return;
//     }

//     setEssayStatus('drafting');
//     setEssayStep(`Found ${capped.length} questions. Drafting with AI...`);
//     try {
//       // ── Step 1: Submit job (returns in <100ms) ──────────────────────────
//       const startRes = await api.post(
//         '/scholarships/draft_essays/',
//         { prompts: capped },
//         { headers: { Authorization: `Bearer ${token}` } }
//       );

//       // ── Bug 3: Original code accessed startRes.data.job_id without
//       // checking. If the backend returned an unexpected shape, job_id
//       // would be undefined and polling would query /status/undefined/
//       // in a silent infinite loop. ──────────────────────────────────────────

//       const jobId = startRes.data?.job_id;
//       if (!jobId) {
//         throw new Error('Server did not return a job ID. Please try again.');
//       }

//       setEssayStep('AI is drafting your essays…');

//       // ── Step 2: Poll until Celery chord finishes ────────────────────────
//       const results = await pollForResults(jobId, token, setEssayStep);

//       // ── Bug 4: Original filtered on `d.draft` being truthy — an empty
//       // string "" is falsy, so a valid but blank draft would be excluded.
//       // The real failure signal is confidence === 'failed', use that. ────────

//       const successful = (results.drafts || []).filter(
//         d => d.confidence !== 'failed'
//       );

//       if (successful.length === 0) {
//         setEssayStatus('error');
//         setEssayError('AI could not draft any essays. Try completing more of your profile.');
//         return;
//       }

//       const merged = successful.map(draft => {
//         const meta = prompts.find(p => p.id === draft.id) || {};
//         return {
//           ...draft,
//           prompt:    meta.prompt    || '',
//           max_words: meta.max_words || 200,
//         };
//       });

//       setEssayStatus('ready');
//       reviewModal.openModal(merged);

//     } catch (err) {
//       console.error('[ScholarScope] Essay drafting error:', err);
//       setEssayStatus('error');
//       // ── Bug 5: err.message can be undefined for AxiosErrors.
//       // Check err.response?.data?.error first. ────────────────────────────
//       setEssayError(
//         err.response?.data?.error ||
//         err.message              ||
//         'AI drafting failed. Please try again.'
//       );
//     }

//   // ── Bug 6: reviewModal was missing from the dependency array.
//   // useCallback with a stale closure over reviewModal means openModal
//   // could call an old instance of the modal after a re-render. ─────────────
//   }, [getToken, reviewModal]);


//   const resetEssay = useCallback(() => {
//     setEssayStatus('idle');
//     setEssayStep('');
//     setEssayError('');
//     getActiveTabId()
//       .then(tabId => sendTabMessage(tabId, { action: 'CLEAR_ESSAY_HIGHLIGHTS' }))
//       .catch(() => {}); // Tab may have navigated away — ignore
//   }, []);

//   return { essayStatus, essayStep, essayError, handleAIEssayDrafting, resetEssay };
// }


// // ── Chrome API helpers ────────────────────────────────────────────────────────
// // Wrapping in Promises lets the hook use async/await instead of nested
// // callbacks. These are plain functions, not hooks.

// function getActiveTabId() {
//   return new Promise((resolve, reject) => {
//     chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
//       if (chrome.runtime.lastError) return reject(chrome.runtime.lastError);
//       const tabId = tabs[0]?.id;
//       if (!tabId) return reject(new Error('No active tab found.'));
//       resolve(tabId);
//     });
//   });
// }

// function sendTabMessage(tabId, message) {
//   return new Promise((resolve, reject) => {
//     chrome.tabs.sendMessage(tabId, message, (response) => {
//       if (chrome.runtime.lastError) return reject(chrome.runtime.lastError);
//       resolve(response);
//     });
//   });
// }


// // ── Inject approved drafts ────────────────────────────────────────────────────

// export async function injectApprovedDrafts(approvedDrafts, onDone) {
//   // ── Bug 7: Original was a void function — callers couldn't await it
//   // or catch errors. Making it async lets App.jsx show injection errors
//   // in the modal instead of silently failing. ─────────────────────────────

//   try {
//     const tabId   = await getActiveTabId();
//     const writeRes = await sendTabMessage(tabId, {
//       action: 'INJECT_ESSAY_DRAFTS',
//       drafts: approvedDrafts,
//     });
//     onDone && onDone(writeRes);
//     return writeRes;
//   } catch (err) {
//     console.error('[ScholarScope] Injection failed:', err);
//     throw err;
//   }
// }


// // ── UI Panel ──────────────────────────────────────────────────────────────────

// export function EssayDraftPanel({ status, step, error, onDraft, onReset }) {
//   const isWorking = status === 'scanning' || status === 'drafting';

//   return (
//     <div className="essay-panel">
//       <div className="essay-panel__header">
//         <span className="essay-panel__label">
//           <Sparkles size={13} />
//           AI Essay Assistant
//         </span>
//       </div>

//       {(status === 'idle' || status === 'ready') && (
//         <button className="essay-btn" onClick={onDraft}>
//           <Sparkles size={14} />
//           {status === 'ready' ? 'Draft Again' : 'Draft Essay Responses'}
//         </button>
//       )}

//       {isWorking && (
//         <div className="essay-panel__progress">
//           <Loader2 size={13} className="spin" />
//           <span>{step || 'Working…'}</span>
//         </div>
//       )}

//       {status === 'error' && (
//         <div className="essay-panel__error">
//           <AlertCircle size={13} />
//           <span className="essay-panel__error-text">{error}</span>
//           {/* ── Bug 8: Original retry called onDraft without resetting state,
//               so the error UI would flicker and state would be inconsistent.
//               Reset first, then draft. ────────────────────────────────────── */}
//           <button
//             className="essay-panel__retry"
//             onClick={() => { onReset?.(); onDraft(); }}
//           >
//             Retry
//           </button>
//         </div>
//       )}
//     </div>
//   );
// }
// src/components/EssayDraftPanel.jsx
import { useState, useCallback } from 'react';
import { Sparkles, Loader2, AlertCircle } from 'lucide-react';
import api from '../api';

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


export function useEssayDrafter({ getToken, reviewModal }) {
  const [essayStatus, setEssayStatus] = useState('idle');
  const [essayStep,   setEssayStep]   = useState('');
  const [essayError,  setEssayError]  = useState('');

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

    // Deduplicate by prompt text (same question detected multiple times)
    const seen = new Set();
    const uniquePrompts = rawPrompts.filter(p => {
      const key = p.prompt.trim().toLowerCase().slice(0, 100);
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });

    // Hard cap at 10
    // ── FIX: name this variable `promptsToSend` so the merge step below
    // can reference it correctly. The previous version named it `capped`
    // then referenced `prompts` in the merge — ReferenceError at runtime. ──
    const promptsToSend = uniquePrompts.slice(0, 10);

    if (promptsToSend.length === 0) {
      setEssayStatus('error');
      setEssayError('No empty essay boxes found on this page.');
      return;
    }

    setEssayStatus('drafting');
    setEssayStep(`Found ${promptsToSend.length} question${promptsToSend.length > 1 ? 's' : ''}. Drafting with AI…`);

    try {
      const startRes = await api.post(
        '/scholarships/draft_essays/',
        { prompts: promptsToSend },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      const jobId = startRes.data?.job_id;
      if (!jobId) {
        throw new Error('Server did not return a job ID. Please try again.');
      }

      setEssayStep('AI is drafting your essays…');

      const results = await pollForResults(jobId, token, setEssayStep);

      const successful = (results.drafts || []).filter(
        d => d.confidence !== 'failed'
      );

      if (successful.length === 0) {
        setEssayStatus('error');
        setEssayError('AI could not draft any essays. Try completing more of your profile.');
        return;
      }

      // ── FIX: was `prompts.find(...)` — undefined variable. Now correctly
      // references `promptsToSend` which holds the array we sent to the API. ──
      const merged = successful.map(draft => {
        const meta = promptsToSend.find(p => p.id === draft.id) || {};
        return {
          ...draft,
          prompt:    meta.prompt    || '',
          max_words: meta.max_words || 200,
        };
      });

      setEssayStatus('ready');
      reviewModal.openModal(merged);

    } catch (err) {
      console.error('[ScholarScope] Essay drafting error:', err);
      setEssayStatus('error');
      setEssayError(
        err.response?.data?.error ||
        err.message              ||
        'AI drafting failed. Please try again.'
      );
    }

  }, [getToken, reviewModal]);


  const resetEssay = useCallback(() => {
    setEssayStatus('idle');
    setEssayStep('');
    setEssayError('');
    getActiveTabId()
      .then(tabId => sendTabMessage(tabId, { action: 'CLEAR_ESSAY_HIGHLIGHTS' }))
      .catch(() => {});
  }, []);

  return { essayStatus, essayStep, essayError, handleAIEssayDrafting, resetEssay };
}


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


export async function injectApprovedDrafts(approvedDrafts, onDone) {
  try {
    const tabId    = await getActiveTabId();
    const writeRes = await sendTabMessage(tabId, {
      action: 'INJECT_ESSAY_DRAFTS',
      drafts: approvedDrafts,
    });
    onDone && onDone(writeRes);
    return writeRes;
  } catch (err) {
    console.error('[ScholarScope] Injection failed:', err);
    throw err;
  }
}


export function EssayDraftPanel({ status, step, error, onDraft, onReset }) {
  const isWorking = status === 'scanning' || status === 'drafting';

  return (
    <div className="essay-panel">
      <div className="essay-panel__header">
        <span className="essay-panel__label">
          <Sparkles size={13} />
          AI Essay Assistant
        </span>
      </div>

      {(status === 'idle' || status === 'ready') && (
        <button className="essay-btn" onClick={onDraft}>
          <Sparkles size={14} />
          {status === 'ready' ? 'Draft Again' : 'Draft Essay Responses'}
        </button>
      )}

      {isWorking && (
        <div className="essay-panel__progress">
          <Loader2 size={13} className="spin" />
          <span>{step || 'Working…'}</span>
        </div>
      )}

      {status === 'error' && (
        <div className="essay-panel__error">
          <AlertCircle size={13} />
          <span className="essay-panel__error-text">{error}</span>
          <button
            className="essay-panel__retry"
            onClick={() => { onReset?.(); onDraft(); }}
          >
            Retry
          </button>
        </div>
      )}
    </div>
  );
}