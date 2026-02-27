// // console.log("ScholarScope Companion loaded on:", window.location.hostname);

// // const SCHOLARSCOPE_ORIGINS = [
// //   'http://localhost:5173',
// //   'http://127.0.0.1:5173',
// //   // add your production domain here
// // ];

// // if (SCHOLARSCOPE_ORIGINS.includes(window.location.origin)) {
// //   document.documentElement.setAttribute('data-scholarscope-installed', 'true');

// //   const token = window.localStorage.getItem('access_token');
// //   if (token) chrome.runtime.sendMessage({ action: 'SYNC_TOKEN', token });

// //   window.addEventListener('storage', (e) => {
// //     if (e.key !== 'access_token') return;
// //     if (e.newValue) chrome.runtime.sendMessage({ action: 'SYNC_TOKEN', token: e.newValue });
// //     else            chrome.runtime.sendMessage({ action: 'CLEAR_TOKEN' });
// //   });
// // }

// // // ── Message listener ──────────────────────────────────────────────────────────
// // chrome.runtime.onMessage.addListener((request, _sender, sendResponse) => {

// //   if (request.action === 'SCRAPE_METADATA') {
// //     sendResponse({
// //       title:       document.title || '',
// //       url:         window.location.href,
// //       description: document.querySelector('meta[name="description"]')?.content || '',
// //     });
// //     return false;
// //   }

// //   if (request.action === 'DEEP_SCRAPE') {
// //     (async () => {
// //       const currentUrl = window.location.href;
// //       const origin     = window.location.origin;

// //       const KEYWORDS = ['eligibility', 'requirements', 'apply', 'criteria', 'benefits', 'award'];
// //       const seen  = new Set([currentUrl]);
// //       const links = [];

// //       for (const a of document.querySelectorAll('a[href]')) {
// //         if (links.length >= 3) break;
// //         const href = a.href;
// //         const text = a.innerText.toLowerCase();
// //         if (href.startsWith(origin) && !seen.has(href) && KEYWORDS.some(kw => text.includes(kw) || href.toLowerCase().includes(kw))) {
// //           seen.add(href);
// //           links.push(href);
// //         }
// //       }

// //       let combinedHTML = document.documentElement.outerHTML;

// //       for (const url of links) {
// //         try {
// //           const res  = await fetch(url, { credentials: 'omit' });
// //           const html = await res.text();
// //           combinedHTML += `\n\n<!-- SUB-PAGE: ${url} -->\n` + html;
// //         } catch {
// //           console.warn('ScholarScope: skipped', url);
// //         }
// //       }

// //       sendResponse({ html: combinedHTML, url: currentUrl, title: document.title });
// //     })();
// //     return true; // async
// //   }

// //   if (request.action === 'EXTRACT_ESSAY_PROMPTS') {
// //     const prompts = extractEssayPrompts();
// //     sendResponse({ prompts });
// //     return false; // synchronous
// //   }

// //   if (request.action === 'INJECT_ESSAY_DRAFTS') {
// //     const result = injectEssayDrafts(request.drafts || []);
// //     sendResponse(result);
// //     return false;
// //   }

// //   // ── ACTION 3: Clear all injected highlights (user wants to reset) ─────────
// //   if (request.action === 'CLEAR_ESSAY_HIGHLIGHTS') {
// //     clearHighlights();
// //     sendResponse({ ok: true });
// //     return false;
// //   }

// // });

// // // function extractEssayPrompts() {
// // //   const prompts = [];
// // //   const textareas = document.querySelectorAll('textarea:not([data-scholarscope-skip])');

// // //   textareas.forEach((ta, index) => {
// // //     // Skip pre-filled boxes — the user already wrote something
// // //     if (ta.value.trim().length > 20) return;
// // //     // Skip hidden / very small boxes (likely honeypots or comment fields)
// // //     if (!isVisible(ta)) return;
// // //     if ((ta.rows || 0) < 2 && ta.offsetHeight < 60) return;

// // //     const promptText = detectPromptText(ta);
// // //     if (!promptText || promptText.length < 15) return;

// // //     const uniqueId = `scholarscope-ta-${index}-${Date.now()}`;
// // //     ta.setAttribute('data-scholarscope-id', uniqueId);

// // //     // Try to detect a word/character limit hint near the textarea
// // //     const maxWords = detectWordLimit(ta);

// // //     prompts.push({
// // //       id:        uniqueId,
// // //       prompt:    promptText.trim(),
// // //       max_words: maxWords,
// // //       // Send the placeholder too — helps the LLM match tone
// // //       placeholder: ta.placeholder || '',
// // //     });
// // //   });

// // //   return prompts;
// // // }

// // function extractEssayPrompts() {
// //   if (window.location.hostname === 'localhost' || 
// //       window.location.hostname === '127.0.0.1') {
// //     return [];
// //   }

// //   const prompts = [];
// //   const textareas = document.querySelectorAll('textarea:not([data-scholarscope-skip])');

// //   textareas.forEach((ta, index) => {
// //     // 1. Check if we already tagged this specific element in a previous scan
// //     let uniqueId = ta.getAttribute('data-scholarscope-id');
    
// //     // 2. Filters (keep your existing visibility logic)
// //     if (ta.value.trim().length > 50) return; // ignore if user already wrote a lot
// //     if (!isVisible(ta)) return;
// //     if ((ta.rows || 0) < 2 && ta.offsetHeight < 60) return;

// //     const promptText = detectPromptText(ta);
// //     if (!promptText || promptText.length < 15) return;

// //     // 3. FIX: Only create a new ID if one doesn't exist
// //     // This prevents the "40 essays" bug when clicking the popup multiple times
// //     if (!uniqueId) {
// //       // Use a hash of the prompt text so the same question always gets the same ID
// //       // even if DOM order changes between scans
// //       const hashSource = (promptText + (ta.name || ta.id || '')).trim().toLowerCase();
// //       const hash = hashSource.split('').reduce((acc, c) => {
// //         return ((acc << 5) - acc + c.charCodeAt(0)) | 0;
// //       }, 0);
// //       uniqueId = `scholarscope-ta-${Math.abs(hash)}`;
// //       ta.setAttribute('data-scholarscope-id', uniqueId);
// //     }

// //     const maxWords = detectWordLimit(ta);

// //     prompts.push({
// //       id: uniqueId,
// //       prompt: promptText.trim(),
// //       max_words: maxWords,
// //       placeholder: ta.placeholder || '',
// //     });
// //   });

// //   return prompts;
// // }

// // function detectPromptText(ta) {
// //   // 1. Explicit <label for="id">

// //   const blacklist = /chat|support|feedback|note|comment|message|search/i;
// //   if (blacklist.test(ta.id) || blacklist.test(ta.name) || blacklist.test(ta.placeholder)) {
// //     return null; 
// //   }

// //   if (ta.id) {
// //     const label = document.querySelector(`label[for="${CSS.escape(ta.id)}"]`);
// //     if (label) return cleanText(label.innerText);
// //   }

// //   // 2. aria-label / aria-labelledby
// //   if (ta.getAttribute('aria-label')) return cleanText(ta.getAttribute('aria-label'));
// //   const labelledById = ta.getAttribute('aria-labelledby');
// //   if (labelledById) {
// //     const el = document.getElementById(labelledById);
// //     if (el) return cleanText(el.innerText);
// //   }

// //   // 3. Closest wrapping <label>
// //   const parentLabel = ta.closest('label');
// //   if (parentLabel) return cleanText(parentLabel.innerText);

// //   // 4. Walk up the DOM — find the nearest preceding heading / paragraph
// //   const candidate = findNearestPromptElement(ta);
// //   if (candidate) return cleanText(candidate.innerText);

// //   // 5. Placeholder fallback (least reliable)
// //   if (ta.placeholder && ta.placeholder.length > 15) {
// //     return cleanText(ta.placeholder);
// //   }

// //   return null;
// // }


// // // Walk up to 5 ancestor levels; at each level take the last preceding sibling
// // // that looks like a question (h1-h6, p, div, li, legend, span with real text).
// // function findNearestPromptElement(ta) {
// //   const PROMPT_TAGS   = new Set(['H1','H2','H3','H4','H5','H6','P','LEGEND','LI']);
// //   const QUESTION_RE   = /\?|describe|explain|tell us|why|how|what|share|discuss/i;
// //   const MIN_LEN       = 15;
// //   const MAX_ANCESTORS = 5;

// //   let node = ta;
// //   for (let depth = 0; depth < MAX_ANCESTORS; depth++) {
// //     node = node.parentElement;
// //     if (!node) break;

// //     // Walk backwards through siblings at this level
// //     let sibling = ta.previousElementSibling || node.previousElementSibling;
// //     while (sibling) {
// //       const text = sibling.innerText?.trim() || '';
// //       if (
// //         text.length > MIN_LEN &&
// //         (PROMPT_TAGS.has(sibling.tagName) || QUESTION_RE.test(text))
// //       ) {
// //         return sibling;
// //       }
// //       sibling = sibling.previousElementSibling;
// //     }
// //   }
// //   return null;
// // }


// // // ─────────────────────────────────────────────────────────────────────────────
// // // detectWordLimit — looks for hints like "max 500 words" near the textarea
// // // ─────────────────────────────────────────────────────────────────────────────
// // function detectWordLimit(ta) {
// //   const DEFAULT = 200;
// //   const LIMIT_RE = /(\d{2,4})\s*(?:words?|characters?|chars?)/i;

// //   // Check placeholder, aria-label, title attributes
// //   const attrs = [ta.placeholder, ta.getAttribute('aria-label'), ta.title].filter(Boolean);
// //   for (const str of attrs) {
// //     const m = str.match(LIMIT_RE);
// //     if (m) return parseInt(m[1], 10);
// //   }

// //   // Check nearby text (within 200px visually)
// //   const rect = ta.getBoundingClientRect();
// //   const nearby = document.querySelectorAll('p, span, small, div');
// //   for (const el of nearby) {
// //     const elRect = el.getBoundingClientRect();
// //     const dist = Math.abs(elRect.bottom - rect.top) + Math.abs(elRect.left - rect.left);
// //     if (dist < 200) {
// //       const m = (el.innerText || '').match(LIMIT_RE);
// //       if (m) return parseInt(m[1], 10);
// //     }
// //   }

// //   return DEFAULT;
// // }


// // // ─────────────────────────────────────────────────────────────────────────────
// // // injectEssayDrafts
// // // ─────────────────────────────────────────────────────────────────────────────
// // function injectEssayDrafts(drafts) {
// //   let filledCount  = 0;
// //   const failedIds  = [];

// //   drafts.forEach(({ id, draft, confidence }) => {
// //     if (!draft) return;

// //     const ta = document.querySelector(`textarea[data-scholarscope-id="${id}"]`);
// //     if (!ta) { failedIds.push(id); return; }

// //     // Use execCommand so undo (Ctrl+Z) works in the app
// //     ta.focus();
// //     ta.select();
// //     const inserted = document.execCommand('insertText', false, draft);

// //     // execCommand is deprecated in some browsers — fallback to direct assignment
// //     if (!inserted || ta.value !== draft) {
// //       ta.value = draft;
// //     }

// //     // Fire all the events a modern SPA might be listening on
// //     ['input', 'change', 'blur', 'keyup'].forEach(eventName => {
// //       ta.dispatchEvent(new Event(eventName, { bubbles: true }));
// //     });
// //     // React synthetic event compatibility
// //     const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
// //       window.HTMLTextAreaElement.prototype, 'value'
// //     )?.set;
// //     if (nativeInputValueSetter) {
// //       nativeInputValueSetter.call(ta, draft);
// //       ta.dispatchEvent(new Event('input', { bubbles: true }));
// //     }

// //     // Visual cue — colour-coded by AI confidence
// //     const borderColor = confidence === 'high'   ? '#10b981'  // green
// //                       : confidence === 'medium' ? '#f59e0b'  // amber
// //                       :                           '#f87171'; // red/low
    
// //     ta.style.cssText += `
// //       border: 2px solid ${borderColor} !important;
// //       background-color: rgba(168, 85, 247, 0.04) !important;
// //       transition: border-color 0.3s ease;
// //     `;

// //     // Add a small floating badge so the user knows AI wrote this
// //     injectBadge(ta, confidence);

// //     filledCount++;
// //   });

// //   return { count: filledCount, failed: failedIds };
// // }


// // // ─────────────────────────────────────────────────────────────────────────────
// // // injectBadge — floating "AI Draft" label above the textarea
// // // ─────────────────────────────────────────────────────────────────────────────
// // function injectBadge(ta, confidence) {
// //   // Remove any existing badge for this element
// //   const existingBadge = ta.parentElement?.querySelector('.scholarscope-badge');
// //   if (existingBadge) existingBadge.remove();

// //   const badge = document.createElement('div');
// //   badge.className = 'scholarscope-badge';
// //   badge.setAttribute('data-scholarscope-badge', 'true');

// //   const confidenceLabel = { high: 'High', medium: 'Medium', low: 'Low' }[confidence] || '?';
// //   badge.innerHTML = `
// //     <span style="font-size:12px">✨</span>
// //     AI Draft · Confidence: <strong>${confidenceLabel}</strong>
// //     &nbsp;·&nbsp;
// //     <span 
// //       style="cursor:pointer;text-decoration:underline" 
// //       onclick="this.closest('[data-scholarscope-badge]').remove(); 
// //                document.querySelector('textarea[data-scholarscope-id=&quot;${ta.getAttribute('data-scholarscope-id')}&quot;]').value = '';
// //                document.querySelector('textarea[data-scholarscope-id=&quot;${ta.getAttribute('data-scholarscope-id')}&quot;]').dispatchEvent(new Event('input',{bubbles:true}));"
// //     >Clear</span>
// //   `;

// //   badge.style.cssText = `
// //     position: relative;
// //     display: inline-flex;
// //     align-items: center;
// //     gap: 4px;
// //     background: rgba(168,85,247,0.1);
// //     border: 1px solid rgba(168,85,247,0.35);
// //     border-radius: 4px;
// //     color: #7c3aed;
// //     font-family: system-ui, sans-serif;
// //     font-size: 11px;
// //     padding: 3px 8px;
// //     margin-bottom: 4px;
// //     z-index: 9999;
// //   `;

// //   ta.insertAdjacentElement('beforebegin', badge);
// // }


// // // ─────────────────────────────────────────────────────────────────────────────
// // // clearHighlights — remove all ScholarScope visual decorations
// // // ─────────────────────────────────────────────────────────────────────────────
// // function clearHighlights() {
// //   document.querySelectorAll('.scholarscope-badge').forEach(el => el.remove());
// //   document.querySelectorAll('textarea[data-scholarscope-id]').forEach(ta => {
// //     ta.style.border = '';
// //     ta.style.backgroundColor = '';
// //     ta.removeAttribute('data-scholarscope-id');
// //   });
// // }


// // // Utils
// // function isVisible(el) {
// //   const style = getComputedStyle(el);
// //   const rect = el.getBoundingClientRect();

// //   return (
// //     style.display !== 'none' &&
// //     style.visibility !== 'hidden' &&
// //     style.opacity !== '0' &&
// //     el.offsetParent !== null &&
// //     rect.width > 20 &&  // Ignore tiny/hidden textareas
// //     rect.height > 20 && // Ignore honeypots
// //     rect.top >= 0       // Ignore elements pushed off-screen
// //   );
// // }

// // function cleanText(str) {
// //   return str.replace(/\s+/g, ' ').replace(/[\r\n]+/g, ' ').trim();
// // }

// // function hasCollapsedAncestor(el) {
// //   let node = el.parentElement;
// //   while (node && node !== document.documentElement) {
// //     const style = getComputedStyle(node);

// //     if (style.display === 'none' || style.visibility === 'hidden') return true;

// //     if (style.overflow === 'hidden' && node.offsetHeight === 0 && node.offsetWidth > 0) return true;

// //     if (style.overflow === 'hidden' && parseFloat(style.maxHeight) === 0) return true;

// //     // ADD: catches transform-based collapse (scaleY, translateY off-screen)
// //     if (style.transform && style.transform.includes('scaleY(0)')) return true;

// //     // ADD: catches aria-hidden sections (screen-reader hidden = visually hidden)
// //     if (node.getAttribute('aria-hidden') === 'true') return true;

// //     node = node.parentElement;
// //   }
// //   return false;
// // }

// // src/content.js
// // Injected into every tab by the manifest's content_scripts declaration.
// // Two jobs:
// //   A) On ScholarScope web app tabs: watch localStorage for auth tokens
// //      and forward them to background.js so the popup stays logged in.
// //   B) On any tab: respond to messages from the popup (scrape, extract
// //      essay prompts, inject drafts, clear highlights).

// console.log('[ScholarScope] content script loaded on:', window.location.hostname);

// // ── A. Token sync (only on the ScholarScope web app) ─────────────────────────
// // Add every origin where your web app might run. The extension popup is at
// // a chrome-extension:// URL and never matches these, so token sync only
// // fires from real web app tabs.
// const SCHOLARSCOPE_ORIGINS = [
//   'http://localhost:5173',
//   'http://127.0.0.1:5173',
//   'http://localhost:3000',   // common alternative dev port
//   // 'https://app.scholarscope.io', // add production domain here
// ];

// if (SCHOLARSCOPE_ORIGINS.includes(window.location.origin)) {
//   // Mark the page so the web app knows the extension is installed
//   document.documentElement.setAttribute('data-scholarscope-installed', 'true');

//   // ── FIX: check both 'access_token' and 'auth_token' ──────────────────────
//   // Django REST framework / dj-rest-auth typically stores the token under
//   // 'access_token' (JWT) or 'auth_token' (Knox/Token auth). Check both so
//   // we don't miss whichever key your web app uses.
//   const syncTokenFromStorage = () => {
//     const token =
//       window.localStorage.getItem('access_token') ||
//       window.localStorage.getItem('auth_token')   ||
//       window.localStorage.getItem('token');        // generic fallback

//     if (token) {
//       chrome.runtime.sendMessage({ action: 'SYNC_TOKEN', token }, (res) => {
//         if (chrome.runtime.lastError) {
//           // Background service worker may be sleeping — this is fine,
//           // it'll wake on next message
//           console.warn('[ScholarScope] Token sync deferred:', chrome.runtime.lastError.message);
//         } else {
//           console.log('[ScholarScope] Token synced to extension:', res);
//         }
//       });
//     }
//   };

//   // Sync immediately on page load (covers hard refresh after login)
//   syncTokenFromStorage();

//   // Sync whenever localStorage changes (covers login/logout without page reload)
//   window.addEventListener('storage', (e) => {
//     const tokenKeys = ['access_token', 'auth_token', 'token'];
//     if (!tokenKeys.includes(e.key)) return;

//     if (e.newValue) {
//       chrome.runtime.sendMessage({ action: 'SYNC_TOKEN', token: e.newValue });
//     } else {
//       // Key was deleted — user logged out
//       chrome.runtime.sendMessage({ action: 'CLEAR_TOKEN' });
//     }
//   });
// }

// // ── B. Message listener (all tabs) ───────────────────────────────────────────
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
//         if (
//           href.startsWith(origin) &&
//           !seen.has(href) &&
//           KEYWORDS.some(kw => text.includes(kw) || href.toLowerCase().includes(kw))
//         ) {
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
//           console.warn('[ScholarScope] skipped sub-page:', url);
//         }
//       }

//       sendResponse({ html: combinedHTML, url: currentUrl, title: document.title });
//     })();
//     return true; // async — keep channel open
//   }

//   if (request.action === 'EXTRACT_ESSAY_PROMPTS') {
//     sendResponse({ prompts: extractEssayPrompts() });
//     return false;
//   }

//   if (request.action === 'INJECT_ESSAY_DRAFTS') {
//     sendResponse(injectEssayDrafts(request.drafts || []));
//     return false;
//   }

//   if (request.action === 'CLEAR_ESSAY_HIGHLIGHTS') {
//     clearHighlights();
//     sendResponse({ ok: true });
//     return false;
//   }

// });

// // ── extractEssayPrompts ───────────────────────────────────────────────────────
// function extractEssayPrompts() {
//   const prompts = [];
//   const idsSeen = new Set();
//   const textareas = document.querySelectorAll('textarea:not([data-scholarscope-skip])');

//   textareas.forEach((ta) => {
//     if (ta.value.trim().length > 50) return;
//     if (!isVisible(ta)) return;
//     if (hasCollapsedAncestor(ta)) return;
//     if ((ta.rows || 0) < 2 && ta.offsetHeight < 60) return;

//     const promptText = detectPromptText(ta);
//     if (!promptText || promptText.length < 15) return;

//     let uniqueId = ta.getAttribute('data-scholarscope-id');
//     if (!uniqueId) {
//       const hashSource = (promptText + (ta.name || ta.id || '')).trim().toLowerCase();
//       const hash = hashSource.split('').reduce((acc, c) => ((acc << 5) - acc + c.charCodeAt(0)) | 0, 0);
//       uniqueId = `scholarscope-ta-${Math.abs(hash)}`;
//       ta.setAttribute('data-scholarscope-id', uniqueId);
//     }

//     if (idsSeen.has(uniqueId)) return;
//     idsSeen.add(uniqueId);

//     prompts.push({
//       id:          uniqueId,
//       prompt:      promptText.trim(),
//       max_words:   detectWordLimit(ta),
//       placeholder: ta.placeholder || '',
//     });
//   });

//   return prompts;
// }

// // ── hasCollapsedAncestor ──────────────────────────────────────────────────────
// // Catches accordion/tab patterns that hide content without display:none.
// function hasCollapsedAncestor(el) {
//   let node = el.parentElement;
//   while (node && node !== document.documentElement) {
//     const style = getComputedStyle(node);

//     if (style.display === 'none' || style.visibility === 'hidden') return true;

//     // overflow:hidden + zero height = collapsed accordion
//     if (style.overflow === 'hidden' && node.offsetHeight === 0 && node.offsetWidth > 0) return true;

//     // CSS max-height:0 collapse
//     if (style.overflow === 'hidden' && parseFloat(style.maxHeight) === 0) return true;

//     // CSS transform collapse (scaleY(0))
//     if (style.transform && style.transform.includes('scaleY(0)')) return true;

//     // aria-hidden — visually hidden from assistive tech, usually also invisible
//     if (node.getAttribute('aria-hidden') === 'true') return true;

//     node = node.parentElement;
//   }
//   return false;
// }

// // ── detectPromptText ──────────────────────────────────────────────────────────
// function detectPromptText(ta) {
//   const blacklist = /chat|support|feedback|note|comment|message|search/i;
//   if (blacklist.test(ta.id) || blacklist.test(ta.name) || blacklist.test(ta.placeholder)) return null;

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

//   if (ta.placeholder && ta.placeholder.length > 15) return cleanText(ta.placeholder);

//   return null;
// }

// function findNearestPromptElement(ta) {
//   const PROMPT_TAGS = new Set(['H1','H2','H3','H4','H5','H6','P','LEGEND','LI']);
//   const QUESTION_RE = /\?|describe|explain|tell us|why|how|what|share|discuss/i;
//   const MIN_LEN     = 15;
//   const MAX_DEPTH   = 5;

//   let node = ta;
//   for (let depth = 0; depth < MAX_DEPTH; depth++) {
//     node = node.parentElement;
//     if (!node) break;

//     let sibling = ta.previousElementSibling || node.previousElementSibling;
//     while (sibling) {
//       const text = sibling.innerText?.trim() || '';
//       if (text.length > MIN_LEN && (PROMPT_TAGS.has(sibling.tagName) || QUESTION_RE.test(text))) {
//         return sibling;
//       }
//       sibling = sibling.previousElementSibling;
//     }
//   }
//   return null;
// }

// // ── detectWordLimit ───────────────────────────────────────────────────────────
// function detectWordLimit(ta) {
//   const LIMIT_RE = /(\d{2,4})\s*(?:words?|characters?|chars?)/i;

//   const attrs = [ta.placeholder, ta.getAttribute('aria-label'), ta.title].filter(Boolean);
//   for (const str of attrs) {
//     const m = str.match(LIMIT_RE);
//     if (m) return parseInt(m[1], 10);
//   }

//   const rect = ta.getBoundingClientRect();
//   for (const el of document.querySelectorAll('p, span, small, div')) {
//     const elRect = el.getBoundingClientRect();
//     const dist = Math.abs(elRect.bottom - rect.top) + Math.abs(elRect.left - rect.left);
//     if (dist < 200) {
//       const m = (el.innerText || '').match(LIMIT_RE);
//       if (m) return parseInt(m[1], 10);
//     }
//   }

//   return 200;
// }

// // ── injectEssayDrafts ─────────────────────────────────────────────────────────
// function injectEssayDrafts(drafts) {
//   let filledCount = 0;
//   const failedIds = [];

//   drafts.forEach(({ id, draft, confidence }) => {
//     if (!draft) return;

//     const ta = document.querySelector(`textarea[data-scholarscope-id="${id}"]`);
//     if (!ta) { failedIds.push(id); return; }

//     ta.focus();
//     ta.select();
//     if (!document.execCommand('insertText', false, draft) || ta.value !== draft) {
//       ta.value = draft;
//     }

//     ['input', 'change', 'blur', 'keyup'].forEach(ev =>
//       ta.dispatchEvent(new Event(ev, { bubbles: true }))
//     );

//     // React synthetic event compatibility
//     const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value')?.set;
//     if (nativeSetter) {
//       nativeSetter.call(ta, draft);
//       ta.dispatchEvent(new Event('input', { bubbles: true }));
//     }

//     const borderColor = confidence === 'high' ? '#10b981' : confidence === 'medium' ? '#f59e0b' : '#f87171';
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

// // ── injectBadge ───────────────────────────────────────────────────────────────
// function injectBadge(ta, confidence) {
//   ta.parentElement?.querySelector('.scholarscope-badge')?.remove();

//   const badge = document.createElement('div');
//   badge.className = 'scholarscope-badge';
//   badge.setAttribute('data-scholarscope-badge', 'true');

//   const label = { high: 'High', medium: 'Medium', low: 'Low' }[confidence] || '?';
//   const taId  = ta.getAttribute('data-scholarscope-id');

//   badge.innerHTML = `
//     <span style="font-size:12px">✨</span>
//     AI Draft · Confidence: <strong>${label}</strong>
//     &nbsp;·&nbsp;
//     <span style="cursor:pointer;text-decoration:underline"
//       onclick="this.closest('[data-scholarscope-badge]').remove();
//                var t=document.querySelector('textarea[data-scholarscope-id=&quot;${taId}&quot;]');
//                if(t){t.value='';t.dispatchEvent(new Event('input',{bubbles:true}));}"
//     >Clear</span>
//   `;

//   badge.style.cssText = `
//     position:relative; display:inline-flex; align-items:center; gap:4px;
//     background:rgba(168,85,247,0.1); border:1px solid rgba(168,85,247,0.35);
//     border-radius:4px; color:#7c3aed; font-family:system-ui,sans-serif;
//     font-size:11px; padding:3px 8px; margin-bottom:4px; z-index:9999;
//   `;

//   ta.insertAdjacentElement('beforebegin', badge);
// }

// // ── clearHighlights ───────────────────────────────────────────────────────────
// function clearHighlights() {
//   document.querySelectorAll('.scholarscope-badge').forEach(el => el.remove());
//   document.querySelectorAll('textarea[data-scholarscope-id]').forEach(ta => {
//     ta.style.border = '';
//     ta.style.backgroundColor = '';
//     ta.removeAttribute('data-scholarscope-id');
//   });
// }

// // ── Utilities ─────────────────────────────────────────────────────────────────
// function isVisible(el) {
//   const style = getComputedStyle(el);
//   return (
//     style.display    !== 'none'   &&
//     style.visibility !== 'hidden' &&
//     style.opacity    !== '0'      &&
//     el.offsetParent  !== null
//   );
// }

// function cleanText(str) {
//   return str.replace(/\s+/g, ' ').replace(/[\r\n]+/g, ' ').trim();
// }

// src/content.js — CONTENT SCRIPT ONLY
// Injected into every page tab by manifest content_scripts.
// Do NOT put service worker code here.

// ── Token sync (only on ScholarScope web app tabs) ────────────────────────────
const SCHOLARSCOPE_ORIGINS = [
  'http://localhost:5173',
  'http://127.0.0.1:5173',
  'http://localhost:3000',
  // 'https://app.yourproductiondomain.com',
];

if (SCHOLARSCOPE_ORIGINS.includes(window.location.origin)) {
  document.documentElement.setAttribute('data-scholarscope-installed', 'true');

  // Sync immediately on load (user was already logged in before opening this tab)
  const existingToken =
    window.localStorage.getItem('access_token') ||
    window.localStorage.getItem('auth_token')   ||
    window.localStorage.getItem('token');

  if (existingToken) {
    chrome.runtime.sendMessage({ action: 'SYNC_TOKEN', token: existingToken }, () => {
      if (chrome.runtime.lastError) { /* service worker waking up, safe to ignore */ }
    });
  }

  // Watch for login / logout events
  window.addEventListener('storage', (e) => {
    if (!['access_token', 'auth_token', 'token'].includes(e.key)) return;
    if (e.newValue) {
      chrome.runtime.sendMessage({ action: 'SYNC_TOKEN', token: e.newValue });
    } else {
      chrome.runtime.sendMessage({ action: 'CLEAR_TOKEN' });
    }
  });
}

// ── Message listener ──────────────────────────────────────────────────────────
chrome.runtime.onMessage.addListener((request, _sender, sendResponse) => {

  if (request.action === 'SCRAPE_METADATA') {
    sendResponse({
      title:       document.title || '',
      url:         window.location.href,
      description: document.querySelector('meta[name="description"]')?.content || '',
    });
    return false;
  }

  if (request.action === 'DEEP_SCRAPE') {
    (async () => {
      const currentUrl = window.location.href;
      const origin     = window.location.origin;
      const KEYWORDS   = ['eligibility', 'requirements', 'apply', 'criteria', 'benefits', 'award'];
      const seen       = new Set([currentUrl]);
      const links      = [];

      for (const a of document.querySelectorAll('a[href]')) {
        if (links.length >= 3) break;
        const href = a.href;
        const text = a.innerText.toLowerCase();
        if (href.startsWith(origin) && !seen.has(href) && KEYWORDS.some(kw => text.includes(kw) || href.toLowerCase().includes(kw))) {
          seen.add(href);
          links.push(href);
        }
      }

      let combinedHTML = document.documentElement.outerHTML;
      for (const url of links) {
        try {
          const html = await (await fetch(url, { credentials: 'omit' })).text();
          combinedHTML += `\n\n<!-- SUB-PAGE: ${url} -->\n` + html;
        } catch {
          console.warn('[ScholarScope] skipped:', url);
        }
      }

      sendResponse({ html: combinedHTML, url: currentUrl, title: document.title });
    })();
    return true;
  }

  if (request.action === 'EXTRACT_ESSAY_PROMPTS') {
    sendResponse({ prompts: extractEssayPrompts() });
    return false;
  }

  if (request.action === 'INJECT_ESSAY_DRAFTS') {
    sendResponse(injectEssayDrafts(request.drafts || []));
    return false;
  }

  if (request.action === 'CLEAR_ESSAY_HIGHLIGHTS') {
    clearHighlights();
    sendResponse({ ok: true });
    return false;
  }
});

// ── extractEssayPrompts ───────────────────────────────────────────────────────
function extractEssayPrompts() {
  const prompts = [];
  const idsSeen = new Set();

  document.querySelectorAll('textarea:not([data-scholarscope-skip])').forEach((ta) => {
    if (ta.value.trim().length > 50) return;
    if (!isVisible(ta)) return;
    if (hasCollapsedAncestor(ta)) return;
    if ((ta.rows || 0) < 2 && ta.offsetHeight < 60) return;

    const promptText = detectPromptText(ta);
    if (!promptText || promptText.length < 15) return;

    let uniqueId = ta.getAttribute('data-scholarscope-id');
    if (!uniqueId) {
      const src  = (promptText + (ta.name || ta.id || '')).trim().toLowerCase();
      const hash = src.split('').reduce((acc, c) => ((acc << 5) - acc + c.charCodeAt(0)) | 0, 0);
      uniqueId   = `scholarscope-ta-${Math.abs(hash)}`;
      ta.setAttribute('data-scholarscope-id', uniqueId);
    }

    if (idsSeen.has(uniqueId)) return;
    idsSeen.add(uniqueId);

    prompts.push({ id: uniqueId, prompt: promptText.trim(), max_words: detectWordLimit(ta), placeholder: ta.placeholder || '' });
  });

  return prompts;
}

function hasCollapsedAncestor(el) {
  let node = el.parentElement;
  while (node && node !== document.documentElement) {
    const s = getComputedStyle(node);
    if (s.display === 'none' || s.visibility === 'hidden') return true;
    if (s.overflow === 'hidden' && node.offsetHeight === 0 && node.offsetWidth > 0) return true;
    if (s.overflow === 'hidden' && parseFloat(s.maxHeight) === 0) return true;
    if (s.transform && s.transform.includes('scaleY(0)')) return true;
    if (node.getAttribute('aria-hidden') === 'true') return true;
    node = node.parentElement;
  }
  return false;
}

function detectPromptText(ta) {
  const blacklist = /chat|support|feedback|note|comment|message|search/i;
  if (blacklist.test(ta.id) || blacklist.test(ta.name) || blacklist.test(ta.placeholder)) return null;

  if (ta.id) {
    const label = document.querySelector(`label[for="${CSS.escape(ta.id)}"]`);
    if (label) return cleanText(label.innerText);
  }
  if (ta.getAttribute('aria-label')) return cleanText(ta.getAttribute('aria-label'));
  const lbId = ta.getAttribute('aria-labelledby');
  if (lbId) { const el = document.getElementById(lbId); if (el) return cleanText(el.innerText); }
  const parentLabel = ta.closest('label');
  if (parentLabel) return cleanText(parentLabel.innerText);
  const candidate = findNearestPromptElement(ta);
  if (candidate) return cleanText(candidate.innerText);
  if (ta.placeholder && ta.placeholder.length > 15) return cleanText(ta.placeholder);
  return null;
}

function findNearestPromptElement(ta) {
  const TAGS = new Set(['H1','H2','H3','H4','H5','H6','P','LEGEND','LI']);
  const RE   = /\?|describe|explain|tell us|why|how|what|share|discuss/i;
  let node = ta;
  for (let d = 0; d < 5; d++) {
    node = node.parentElement;
    if (!node) break;
    let sib = ta.previousElementSibling || node.previousElementSibling;
    while (sib) {
      const text = sib.innerText?.trim() || '';
      if (text.length > 15 && (TAGS.has(sib.tagName) || RE.test(text))) return sib;
      sib = sib.previousElementSibling;
    }
  }
  return null;
}

function detectWordLimit(ta) {
  const RE = /(\d{2,4})\s*(?:words?|characters?|chars?)/i;
  for (const str of [ta.placeholder, ta.getAttribute('aria-label'), ta.title].filter(Boolean)) {
    const m = str.match(RE); if (m) return parseInt(m[1], 10);
  }
  const rect = ta.getBoundingClientRect();
  for (const el of document.querySelectorAll('p, span, small, div')) {
    const er = el.getBoundingClientRect();
    if (Math.abs(er.bottom - rect.top) + Math.abs(er.left - rect.left) < 200) {
      const m = (el.innerText || '').match(RE); if (m) return parseInt(m[1], 10);
    }
  }
  return 200;
}

// ── injectEssayDrafts ─────────────────────────────────────────────────────────
function injectEssayDrafts(drafts) {
  let filledCount = 0;
  const failedIds = [];

  drafts.forEach(({ id, draft, confidence }) => {
    if (!draft) return;
    const ta = document.querySelector(`textarea[data-scholarscope-id="${id}"]`);
    if (!ta) { failedIds.push(id); return; }

    ta.focus(); ta.select();
    if (!document.execCommand('insertText', false, draft) || ta.value !== draft) ta.value = draft;

    ['input', 'change', 'blur', 'keyup'].forEach(ev => ta.dispatchEvent(new Event(ev, { bubbles: true })));

    const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value')?.set;
    if (setter) { setter.call(ta, draft); ta.dispatchEvent(new Event('input', { bubbles: true })); }

    const color = confidence === 'high' ? '#10b981' : confidence === 'medium' ? '#f59e0b' : '#f87171';
    ta.style.cssText += `border:2px solid ${color} !important;background-color:rgba(168,85,247,0.04) !important;transition:border-color 0.3s ease;`;
    injectBadge(ta, confidence);
    filledCount++;
  });

  return { count: filledCount, failed: failedIds };
}

function injectBadge(ta, confidence) {
  ta.parentElement?.querySelector('.scholarscope-badge')?.remove();
  const badge = document.createElement('div');
  badge.className = 'scholarscope-badge';
  badge.setAttribute('data-scholarscope-badge', 'true');
  const label = { high: 'High', medium: 'Medium', low: 'Low' }[confidence] || '?';
  const taId  = ta.getAttribute('data-scholarscope-id');
  badge.innerHTML = `<span style="font-size:12px">✨</span> AI Draft · Confidence: <strong>${label}</strong> &nbsp;·&nbsp; <span style="cursor:pointer;text-decoration:underline" onclick="this.closest('[data-scholarscope-badge]').remove();var t=document.querySelector('textarea[data-scholarscope-id=&quot;${taId}&quot;]');if(t){t.value='';t.dispatchEvent(new Event('input',{bubbles:true}));}">Clear</span>`;
  badge.style.cssText = 'position:relative;display:inline-flex;align-items:center;gap:4px;background:rgba(168,85,247,0.1);border:1px solid rgba(168,85,247,0.35);border-radius:4px;color:#7c3aed;font-family:system-ui,sans-serif;font-size:11px;padding:3px 8px;margin-bottom:4px;z-index:9999;';
  ta.insertAdjacentElement('beforebegin', badge);
}

function clearHighlights() {
  document.querySelectorAll('.scholarscope-badge').forEach(el => el.remove());
  document.querySelectorAll('textarea[data-scholarscope-id]').forEach(ta => {
    ta.style.border = ''; ta.style.backgroundColor = ''; ta.removeAttribute('data-scholarscope-id');
  });
}

function isVisible(el) {
  const s = getComputedStyle(el);
  return s.display !== 'none' && s.visibility !== 'hidden' && s.opacity !== '0' && el.offsetParent !== null;
}

function cleanText(str) {
  return str.replace(/\s+/g, ' ').replace(/[\r\n]+/g, ' ').trim();
}