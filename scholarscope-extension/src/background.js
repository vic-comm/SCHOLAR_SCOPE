// chrome.runtime.onInstalled.addListener(() => {
//   chrome.contextMenus.create({ id: 'scholarscope-root', title: 'ScholarScope', contexts: ['selection'] });
//   chrome.contextMenus.create({ parentId: 'scholarscope-root', id: 'add_eligibility',  title: '+ Add to Eligibility',  contexts: ['selection'] });
//   chrome.contextMenus.create({ parentId: 'scholarscope-root', id: 'add_requirements', title: '+ Add to Requirements', contexts: ['selection'] });
//   chrome.contextMenus.create({ parentId: 'scholarscope-root', id: 'set_reward',       title: 'Set as Reward Amount', contexts: ['selection'] });
//   chrome.contextMenus.create({ parentId: 'scholarscope-root', id: 'set_deadline',     title: 'Set as Deadline',      contexts: ['selection'] });
// });

// // ── Context menu clicks ───────────────────────────────────────────────────────
// chrome.contextMenus.onClicked.addListener((info) => {
//   const text = info.selectionText?.trim();
//   if (!text) return;
//   switch (info.menuItemId) {
//     case 'add_eligibility':  appendToDraft('eligibility', text);  break;
//     case 'add_requirements': appendToDraft('requirements', text); break;
//     case 'set_reward':       setDraftField('reward', text);       break;
//     case 'set_deadline':     setDraftField('end_date', text);     break;
//   }
// });

// // ── Draft helpers ─────────────────────────────────────────────────────────────
// function appendToDraft(key, text) {
//   chrome.storage.local.get(['draft'], (r) => {
//     const draft = r.draft || {};
//     const prev  = draft[key] || '';
//     draft[key]  = prev ? `${prev}\n• ${text}` : `• ${text}`;
//     saveDraft(draft);
//   });
// }

// function setDraftField(key, value) {
//   chrome.storage.local.get(['draft'], (r) => {
//     const draft = r.draft || {};
//     draft[key]  = value;
//     saveDraft(draft);
//   });
// }

// function saveDraft(draft) {
//   chrome.storage.local.set({ draft }, () => {
//     chrome.action.setBadgeText({ text: '✓' });
//     chrome.action.setBadgeBackgroundColor({ color: '#16a34a' });
//     setTimeout(() => chrome.action.setBadgeText({ text: '' }), 2000);
//   });
// }

// // ── Token sync messages from web-app ─────────────────────────────────────────
// chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
//   if (msg.action === 'SYNC_TOKEN' && msg.token) {
//     chrome.storage.local.set({ auth_token: msg.token });
//     sendResponse({ ok: true });
//   }
//   if (msg.action === 'CLEAR_TOKEN') {
//     chrome.storage.local.remove('auth_token');
//     sendResponse({ ok: true });
//   }
//   return false;
// });


// const SCHOLARSCOPE_ORIGINS = [
//   'http://localhost:5173',
//   'http://127.0.0.1:5173',
//   // add your production domain here
// ];

// if (SCHOLARSCOPE_ORIGINS.includes(window.location.origin)) {
//   document.documentElement.setAttribute('data-scholarscope-installed', 'true');

//   const token = window.localStorage.getItem('access_token');
//   if (token) chrome.runtime.sendMessage({ action: 'SYNC_TOKEN', token });

//   window.addEventListener('storage', (e) => {
//     if (e.key !== 'access_token') return;
//     if (e.newValue) chrome.runtime.sendMessage({ action: 'SYNC_TOKEN', token: e.newValue });
//     else            chrome.runtime.sendMessage({ action: 'CLEAR_TOKEN' });
//   });
// }

// // ── Message listener ──────────────────────────────────────────────────────────
// chrome.runtime.onMessage.addListener((request, _sender, sendResponse) => {

//   if (request.action === 'SCRAPE_METADATA') {
//     sendResponse({
//       title:       document.title || '',
//       url:         window.location.href,
//       description: document.querySelector('meta[name="description"]')?.content || '',
//     });
//     return false;
//   }

//   if (request.action === 'DEEP_SCRAPE') {
//     (async () => {
//       const currentUrl = window.location.href;
//       const origin     = window.location.origin;

//       const KEYWORDS = ['eligibility', 'requirements', 'apply', 'criteria', 'benefits', 'award'];
//       const seen  = new Set([currentUrl]);
//       const links = [];

//       for (const a of document.querySelectorAll('a[href]')) {
//         if (links.length >= 3) break;
//         const href = a.href;
//         const text = a.innerText.toLowerCase();
//         if (href.startsWith(origin) && !seen.has(href) && KEYWORDS.some(kw => text.includes(kw) || href.toLowerCase().includes(kw))) {
//           seen.add(href);
//           links.push(href);
//         }
//       }

//       let combinedHTML = document.documentElement.outerHTML;

//       for (const url of links) {
//         try {
//           const res  = await fetch(url, { credentials: 'omit' });
//           const html = await res.text();
//           combinedHTML += `\n\n<!-- SUB-PAGE: ${url} -->\n` + html;
//         } catch {
//           console.warn('ScholarScope: skipped', url);
//         }
//       }

//       sendResponse({ html: combinedHTML, url: currentUrl, title: document.title });
//     })();
//     return true;
//   }

//   if (request.action === 'EXTRACT_ESSAY_PROMPTS') {
//     const prompts = extractEssayPrompts();
//     sendResponse({ prompts });
//     return false;
//   }

//   if (request.action === 'INJECT_ESSAY_DRAFTS') {
//     const result = injectEssayDrafts(request.drafts || []);
//     sendResponse(result);
//     return false;
//   }

//   if (request.action === 'CLEAR_ESSAY_HIGHLIGHTS') {
//     clearHighlights();
//     sendResponse({ ok: true });
//     return false;
//   }

// });

// function extractEssayPrompts() {
//   // ── REMOVED: the `if localhost return []` guard that was here previously.
//   // This content script runs in the scholarship site tab, not localhost.
//   // window.location.hostname on portal.thenhef.org is 'portal.thenhef.org',
//   // so the guard never fired there — it was a no-op that only would have
//   // blocked scanning if someone hosted the scholarship site at localhost. ────

//   const prompts = [];
//   const idsSeen = new Set(); // deduplicate within this single scan pass
//   const textareas = document.querySelectorAll('textarea:not([data-scholarscope-skip])');

//   textareas.forEach((ta, index) => {
//     // ── Skip pre-filled boxes ──────────────────────────────────────────────
//     if (ta.value.trim().length > 50) return;

//     // ── Standard visibility check (display:none, visibility:hidden, opacity:0)
//     if (!isVisible(ta)) return;

//     // ── FIX: Skip textareas inside collapsed/hidden ancestor containers ────
//     // The NHEF form uses accordion sections with max-height:0 overflow:hidden.
//     // offsetParent is still non-null for these so isVisible() passes them,
//     // but they're not actually reachable by the user yet.
//     if (hasCollapsedAncestor(ta)) return;

//     // ── Skip tiny boxes (honeypots, comment fields) ────────────────────────
//     if ((ta.rows || 0) < 2 && ta.offsetHeight < 60) return;

//     const promptText = detectPromptText(ta);
//     if (!promptText || promptText.length < 15) return;

//     // ── Stable hash-based ID (same question = same ID across popup opens) ──
//     let uniqueId = ta.getAttribute('data-scholarscope-id');
//     if (!uniqueId) {
//       const hashSource = (promptText + (ta.name || ta.id || '')).trim().toLowerCase();
//       const hash = hashSource.split('').reduce((acc, c) => {
//         return ((acc << 5) - acc + c.charCodeAt(0)) | 0;
//       }, 0);
//       uniqueId = `scholarscope-ta-${Math.abs(hash)}`;
//       ta.setAttribute('data-scholarscope-id', uniqueId);
//     }

//     // ── Skip if this ID already collected in this scan pass ────────────────
//     if (idsSeen.has(uniqueId)) return;
//     idsSeen.add(uniqueId);

//     const maxWords = detectWordLimit(ta);
//     prompts.push({
//       id:          uniqueId,
//       prompt:      promptText.trim(),
//       max_words:   maxWords,
//       placeholder: ta.placeholder || '',
//     });
//   });

//   return prompts;
// }


// // ── hasCollapsedAncestor ──────────────────────────────────────────────────────
// // Walks up the DOM and returns true if any ancestor is visually collapsed.
// // Catches accordion patterns that use max-height:0 + overflow:hidden,
// // which isVisible() misses because offsetParent is still non-null.
// function hasCollapsedAncestor(el) {
//   let node = el.parentElement;
//   while (node && node !== document.documentElement) {
//     const style = getComputedStyle(node);

//     // Explicit hide
//     if (style.display === 'none' || style.visibility === 'hidden') return true;

//     // Accordion / collapse pattern: zero height with hidden overflow
//     if (
//       style.overflow === 'hidden' &&
//       node.offsetHeight === 0 &&
//       node.offsetWidth > 0  // has width but no height — definitely collapsed
//     ) return true;

//     // max-height collapse (common in CSS accordion implementations)
//     if (
//       style.overflow === 'hidden' &&
//       parseFloat(style.maxHeight) === 0
//     ) return true;

//     node = node.parentElement;
//   }
//   return false;
// }


// function detectPromptText(ta) {
//   const blacklist = /chat|support|feedback|note|comment|message|search/i;
//   if (blacklist.test(ta.id) || blacklist.test(ta.name) || blacklist.test(ta.placeholder)) {
//     return null;
//   }

//   if (ta.id) {
//     const label = document.querySelector(`label[for="${CSS.escape(ta.id)}"]`);
//     if (label) return cleanText(label.innerText);
//   }

//   if (ta.getAttribute('aria-label')) return cleanText(ta.getAttribute('aria-label'));
//   const labelledById = ta.getAttribute('aria-labelledby');
//   if (labelledById) {
//     const el = document.getElementById(labelledById);
//     if (el) return cleanText(el.innerText);
//   }

//   const parentLabel = ta.closest('label');
//   if (parentLabel) return cleanText(parentLabel.innerText);

//   const candidate = findNearestPromptElement(ta);
//   if (candidate) return cleanText(candidate.innerText);

//   if (ta.placeholder && ta.placeholder.length > 15) {
//     return cleanText(ta.placeholder);
//   }

//   return null;
// }


// function findNearestPromptElement(ta) {
//   const PROMPT_TAGS = new Set(['H1','H2','H3','H4','H5','H6','P','LEGEND','LI']);
//   const QUESTION_RE = /\?|describe|explain|tell us|why|how|what|share|discuss/i;
//   const MIN_LEN     = 15;
//   const MAX_ANCESTORS = 5;

//   let node = ta;
//   for (let depth = 0; depth < MAX_ANCESTORS; depth++) {
//     node = node.parentElement;
//     if (!node) break;

//     let sibling = ta.previousElementSibling || node.previousElementSibling;
//     while (sibling) {
//       const text = sibling.innerText?.trim() || '';
//       if (
//         text.length > MIN_LEN &&
//         (PROMPT_TAGS.has(sibling.tagName) || QUESTION_RE.test(text))
//       ) {
//         return sibling;
//       }
//       sibling = sibling.previousElementSibling;
//     }
//   }
//   return null;
// }


// function detectWordLimit(ta) {
//   const DEFAULT  = 200;
//   const LIMIT_RE = /(\d{2,4})\s*(?:words?|characters?|chars?)/i;

//   const attrs = [ta.placeholder, ta.getAttribute('aria-label'), ta.title].filter(Boolean);
//   for (const str of attrs) {
//     const m = str.match(LIMIT_RE);
//     if (m) return parseInt(m[1], 10);
//   }

//   const rect = ta.getBoundingClientRect();
//   const nearby = document.querySelectorAll('p, span, small, div');
//   for (const el of nearby) {
//     const elRect = el.getBoundingClientRect();
//     const dist = Math.abs(elRect.bottom - rect.top) + Math.abs(elRect.left - rect.left);
//     if (dist < 200) {
//       const m = (el.innerText || '').match(LIMIT_RE);
//       if (m) return parseInt(m[1], 10);
//     }
//   }

//   return DEFAULT;
// }


// function injectEssayDrafts(drafts) {
//   let filledCount = 0;
//   const failedIds = [];

//   drafts.forEach(({ id, draft, confidence }) => {
//     if (!draft) return;

//     const ta = document.querySelector(`textarea[data-scholarscope-id="${id}"]`);
//     if (!ta) { failedIds.push(id); return; }

//     ta.focus();
//     ta.select();
//     const inserted = document.execCommand('insertText', false, draft);

//     if (!inserted || ta.value !== draft) {
//       ta.value = draft;
//     }

//     ['input', 'change', 'blur', 'keyup'].forEach(eventName => {
//       ta.dispatchEvent(new Event(eventName, { bubbles: true }));
//     });

//     const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
//       window.HTMLTextAreaElement.prototype, 'value'
//     )?.set;
//     if (nativeInputValueSetter) {
//       nativeInputValueSetter.call(ta, draft);
//       ta.dispatchEvent(new Event('input', { bubbles: true }));
//     }

//     const borderColor = confidence === 'high'   ? '#10b981'
//                       : confidence === 'medium' ? '#f59e0b'
//                       :                           '#f87171';

//     ta.style.cssText += `
//       border: 2px solid ${borderColor} !important;
//       background-color: rgba(168, 85, 247, 0.04) !important;
//       transition: border-color 0.3s ease;
//     `;

//     injectBadge(ta, confidence);
//     filledCount++;
//   });

//   return { count: filledCount, failed: failedIds };
// }


// function injectBadge(ta, confidence) {
//   const existingBadge = ta.parentElement?.querySelector('.scholarscope-badge');
//   if (existingBadge) existingBadge.remove();

//   const badge = document.createElement('div');
//   badge.className = 'scholarscope-badge';
//   badge.setAttribute('data-scholarscope-badge', 'true');

//   const confidenceLabel = { high: 'High', medium: 'Medium', low: 'Low' }[confidence] || '?';
//   const taId = ta.getAttribute('data-scholarscope-id');

//   badge.innerHTML = `
//     <span style="font-size:12px">✨</span>
//     AI Draft · Confidence: <strong>${confidenceLabel}</strong>
//     &nbsp;·&nbsp;
//     <span 
//       style="cursor:pointer;text-decoration:underline" 
//       onclick="this.closest('[data-scholarscope-badge]').remove();
//                var t = document.querySelector('textarea[data-scholarscope-id=&quot;${taId}&quot;]');
//                if(t){ t.value=''; t.dispatchEvent(new Event('input',{bubbles:true})); }"
//     >Clear</span>
//   `;

//   badge.style.cssText = `
//     position: relative;
//     display: inline-flex;
//     align-items: center;
//     gap: 4px;
//     background: rgba(168,85,247,0.1);
//     border: 1px solid rgba(168,85,247,0.35);
//     border-radius: 4px;
//     color: #7c3aed;
//     font-family: system-ui, sans-serif;
//     font-size: 11px;
//     padding: 3px 8px;
//     margin-bottom: 4px;
//     z-index: 9999;
//   `;

//   ta.insertAdjacentElement('beforebegin', badge);
// }


// function clearHighlights() {
//   document.querySelectorAll('.scholarscope-badge').forEach(el => el.remove());
//   document.querySelectorAll('textarea[data-scholarscope-id]').forEach(ta => {
//     ta.style.border = '';
//     ta.style.backgroundColor = '';
//     ta.removeAttribute('data-scholarscope-id');
//   });
// }


// function isVisible(el) {
//   const style = getComputedStyle(el);
//   return (
//     style.display     !== 'none'   &&
//     style.visibility  !== 'hidden' &&
//     style.opacity     !== '0'      &&
//     el.offsetParent   !== null
//   );
// }

// function cleanText(str) {
//   return str.replace(/\s+/g, ' ').replace(/[\r\n]+/g, ' ').trim();
// }

// src/background.js — SERVICE WORKER ONLY
// Do NOT import or reference content.js from here.
// crxjs bundles these as separate entry points.

// ── Context menus ─────────────────────────────────────────────────────────────
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.removeAll(() => {
    chrome.contextMenus.create({ id: 'scholarscope-root', title: 'ScholarScope', contexts: ['selection'] });
    chrome.contextMenus.create({ parentId: 'scholarscope-root', id: 'add_eligibility',  title: '+ Add to Eligibility',  contexts: ['selection'] });
    chrome.contextMenus.create({ parentId: 'scholarscope-root', id: 'add_requirements', title: '+ Add to Requirements', contexts: ['selection'] });
    chrome.contextMenus.create({ parentId: 'scholarscope-root', id: 'set_reward',       title: 'Set as Reward Amount', contexts: ['selection'] });
    chrome.contextMenus.create({ parentId: 'scholarscope-root', id: 'set_deadline',     title: 'Set as Deadline',      contexts: ['selection'] });
  });
});

chrome.contextMenus.onClicked.addListener((info) => {
  const text = info.selectionText?.trim();
  if (!text) return;
  switch (info.menuItemId) {
    case 'add_eligibility':  appendToDraft('eligibility', text);  break;
    case 'add_requirements': appendToDraft('requirements', text); break;
    case 'set_reward':       setDraftField('reward', text);       break;
    case 'set_deadline':     setDraftField('end_date', text);     break;
  }
});

function appendToDraft(key, text) {
  chrome.storage.local.get(['draft'], (r) => {
    const draft = r.draft || {};
    draft[key] = draft[key] ? `${draft[key]}\n• ${text}` : `• ${text}`;
    saveDraft(draft);
  });
}

function setDraftField(key, value) {
  chrome.storage.local.get(['draft'], (r) => {
    const draft = r.draft || {};
    draft[key] = value;
    saveDraft(draft);
  });
}

function saveDraft(draft) {
  chrome.storage.local.set({ draft }, () => {
    chrome.action.setBadgeText({ text: '✓' });
    chrome.action.setBadgeBackgroundColor({ color: '#16a34a' });
    setTimeout(() => chrome.action.setBadgeText({ text: '' }), 2000);
  });
}

// ── Token sync ────────────────────────────────────────────────────────────────
// content.js (on the web app tab) sends SYNC_TOKEN here.
// We store it so the popup can read it from chrome.storage.local.
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.action === 'SYNC_TOKEN' && msg.token) {
    // Only accept from real page tabs, not the popup
    if (!sender.tab) { sendResponse({ ok: false }); return false; }
    chrome.storage.local.set({ auth_token: msg.token }, () => sendResponse({ ok: true }));
    return true; // async
  }

  if (msg.action === 'CLEAR_TOKEN') {
    chrome.storage.local.remove('auth_token', () => sendResponse({ ok: true }));
    return true;
  }

  return false;
});