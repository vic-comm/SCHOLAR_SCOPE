// // src/content/index.js
// console.log("ScholarScope Companion Loaded");

// const SCHOLARSCOPE_URLS = ["http://localhost:5173", "http://127.0.0.1:5173"];
// const currentOrigin = window.location.origin;

// // 1. TOKEN HEIST: Sync token from web app to extension
// if (SCHOLARSCOPE_URLS.includes(currentOrigin)) {
//     document.documentElement.setAttribute('data-scholar-scope-installed', 'true');
//     const token = window.localStorage.getItem('access_token');
//     if (token) {
//         // FIXED: Using 'auth_token' to match Login.jsx
//         chrome.storage.local.set({ auth_token: token }, () => {
//             console.log("ScholarScope Extension: Token synced successfully.");
//         });
//     }
// }

// // 2. MAIN LISTENER
// chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  
//   // Action A: Basic Metadata for the manual form
//   if (request.action === "SCRAPE_METADATA") {
//     sendResponse({
//       title: document.title || "",
//       url: window.location.href,
//       description: document.querySelector('meta[name="description"]')?.content || ""
//     });
//     return false; // Sync response
//   }

//   // Action B: The Deep Scrape for the Python Backend
//   if (request.action === "DEEP_SCRAPE") {
//       (async () => {
//           let combinedHTML = document.documentElement.outerHTML;
//           const currentUrl = window.location.href;
          
//           const targetKeywords = ['eligibility', 'requirements', 'apply', 'criteria'];
//           const linksToFetch = new Set();
          
//           document.querySelectorAll('a').forEach(link => {
//               const text = link.innerText.toLowerCase();
//               const href = link.href;
//               if (targetKeywords.some(kw => text.includes(kw)) && href.startsWith(window.location.origin) && href !== currentUrl) {
//                   linksToFetch.add(href);
//               }
//           });

//           const urlsToFetch = Array.from(linksToFetch).slice(0, 3); 
//           for (const url of urlsToFetch) {
//               try {
//                   const response = await fetch(url);
//                   const htmlText = await response.text();
//                   combinedHTML += `\n\n\n\n` + htmlText;
//               } catch (err) {
//                   console.warn("Failed to fetch sub-page:", url);
//               }
//           }

//           sendResponse({ 
//               html: combinedHTML,
//               url: currentUrl,
//               title: document.title
//           });
//       })();
      
//       return true; // Async response
//   }
// });

// src/content/index.js
console.log("ScholarScope Companion loaded on:", window.location.hostname);

const SCHOLARSCOPE_ORIGINS = [
  'http://localhost:5173',
  'http://127.0.0.1:5173',
  // add your production domain here
];

// ── Token Sync ────────────────────────────────────────────────────────────────
if (SCHOLARSCOPE_ORIGINS.includes(window.location.origin)) {
  document.documentElement.setAttribute('data-scholarscope-installed', 'true');

  const token = window.localStorage.getItem('access_token');
  if (token) chrome.runtime.sendMessage({ action: 'SYNC_TOKEN', token });

  window.addEventListener('storage', (e) => {
    if (e.key !== 'access_token') return;
    if (e.newValue) chrome.runtime.sendMessage({ action: 'SYNC_TOKEN', token: e.newValue });
    else            chrome.runtime.sendMessage({ action: 'CLEAR_TOKEN' });
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

      const KEYWORDS = ['eligibility', 'requirements', 'apply', 'criteria', 'benefits', 'award'];
      const seen  = new Set([currentUrl]);
      const links = [];

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
          const res  = await fetch(url, { credentials: 'omit' });
          const html = await res.text();
          combinedHTML += `\n\n<!-- SUB-PAGE: ${url} -->\n` + html;
        } catch {
          console.warn('ScholarScope: skipped', url);
        }
      }

      sendResponse({ html: combinedHTML, url: currentUrl, title: document.title });
    })();
    return true; // async
  }

  if (request.action === 'EXTRACT_ESSAY_PROMPTS') {
    const prompts = extractEssayPrompts();
    sendResponse({ prompts });
    return false; // synchronous
  }

  if (request.action === 'INJECT_ESSAY_DRAFTS') {
    const result = injectEssayDrafts(request.drafts || []);
    sendResponse(result);
    return false;
  }

  // ── ACTION 3: Clear all injected highlights (user wants to reset) ─────────
  if (request.action === 'CLEAR_ESSAY_HIGHLIGHTS') {
    clearHighlights();
    sendResponse({ ok: true });
    return false;
  }

});

function extractEssayPrompts() {
  const prompts = [];
  const textareas = document.querySelectorAll('textarea:not([data-scholarscope-skip])');

  textareas.forEach((ta, index) => {
    // Skip pre-filled boxes — the user already wrote something
    if (ta.value.trim().length > 20) return;
    // Skip hidden / very small boxes (likely honeypots or comment fields)
    if (!isVisible(ta)) return;
    if ((ta.rows || 0) < 2 && ta.offsetHeight < 60) return;

    const promptText = detectPromptText(ta);
    if (!promptText || promptText.length < 15) return;

    const uniqueId = `scholarscope-ta-${index}-${Date.now()}`;
    ta.setAttribute('data-scholarscope-id', uniqueId);

    // Try to detect a word/character limit hint near the textarea
    const maxWords = detectWordLimit(ta);

    prompts.push({
      id:        uniqueId,
      prompt:    promptText.trim(),
      max_words: maxWords,
      // Send the placeholder too — helps the LLM match tone
      placeholder: ta.placeholder || '',
    });
  });

  return prompts;
}

function detectPromptText(ta) {
  // 1. Explicit <label for="id">
  if (ta.id) {
    const label = document.querySelector(`label[for="${CSS.escape(ta.id)}"]`);
    if (label) return cleanText(label.innerText);
  }

  // 2. aria-label / aria-labelledby
  if (ta.getAttribute('aria-label')) return cleanText(ta.getAttribute('aria-label'));
  const labelledById = ta.getAttribute('aria-labelledby');
  if (labelledById) {
    const el = document.getElementById(labelledById);
    if (el) return cleanText(el.innerText);
  }

  // 3. Closest wrapping <label>
  const parentLabel = ta.closest('label');
  if (parentLabel) return cleanText(parentLabel.innerText);

  // 4. Walk up the DOM — find the nearest preceding heading / paragraph
  const candidate = findNearestPromptElement(ta);
  if (candidate) return cleanText(candidate.innerText);

  // 5. Placeholder fallback (least reliable)
  if (ta.placeholder && ta.placeholder.length > 15) {
    return cleanText(ta.placeholder);
  }

  return null;
}


// Walk up to 5 ancestor levels; at each level take the last preceding sibling
// that looks like a question (h1-h6, p, div, li, legend, span with real text).
function findNearestPromptElement(ta) {
  const PROMPT_TAGS   = new Set(['H1','H2','H3','H4','H5','H6','P','LEGEND','LI']);
  const QUESTION_RE   = /\?|describe|explain|tell us|why|how|what|share|discuss/i;
  const MIN_LEN       = 15;
  const MAX_ANCESTORS = 5;

  let node = ta;
  for (let depth = 0; depth < MAX_ANCESTORS; depth++) {
    node = node.parentElement;
    if (!node) break;

    // Walk backwards through siblings at this level
    let sibling = ta.previousElementSibling || node.previousElementSibling;
    while (sibling) {
      const text = sibling.innerText?.trim() || '';
      if (
        text.length > MIN_LEN &&
        (PROMPT_TAGS.has(sibling.tagName) || QUESTION_RE.test(text))
      ) {
        return sibling;
      }
      sibling = sibling.previousElementSibling;
    }
  }
  return null;
}


// ─────────────────────────────────────────────────────────────────────────────
// detectWordLimit — looks for hints like "max 500 words" near the textarea
// ─────────────────────────────────────────────────────────────────────────────
function detectWordLimit(ta) {
  const DEFAULT = 200;
  const LIMIT_RE = /(\d{2,4})\s*(?:words?|characters?|chars?)/i;

  // Check placeholder, aria-label, title attributes
  const attrs = [ta.placeholder, ta.getAttribute('aria-label'), ta.title].filter(Boolean);
  for (const str of attrs) {
    const m = str.match(LIMIT_RE);
    if (m) return parseInt(m[1], 10);
  }

  // Check nearby text (within 200px visually)
  const rect = ta.getBoundingClientRect();
  const nearby = document.querySelectorAll('p, span, small, div');
  for (const el of nearby) {
    const elRect = el.getBoundingClientRect();
    const dist = Math.abs(elRect.bottom - rect.top) + Math.abs(elRect.left - rect.left);
    if (dist < 200) {
      const m = (el.innerText || '').match(LIMIT_RE);
      if (m) return parseInt(m[1], 10);
    }
  }

  return DEFAULT;
}


// ─────────────────────────────────────────────────────────────────────────────
// injectEssayDrafts
// ─────────────────────────────────────────────────────────────────────────────
function injectEssayDrafts(drafts) {
  let filledCount  = 0;
  const failedIds  = [];

  drafts.forEach(({ id, draft, confidence }) => {
    if (!draft) return;

    const ta = document.querySelector(`textarea[data-scholarscope-id="${id}"]`);
    if (!ta) { failedIds.push(id); return; }

    // Use execCommand so undo (Ctrl+Z) works in the app
    ta.focus();
    ta.select();
    const inserted = document.execCommand('insertText', false, draft);

    // execCommand is deprecated in some browsers — fallback to direct assignment
    if (!inserted || ta.value !== draft) {
      ta.value = draft;
    }

    // Fire all the events a modern SPA might be listening on
    ['input', 'change', 'blur', 'keyup'].forEach(eventName => {
      ta.dispatchEvent(new Event(eventName, { bubbles: true }));
    });
    // React synthetic event compatibility
    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
      window.HTMLTextAreaElement.prototype, 'value'
    )?.set;
    if (nativeInputValueSetter) {
      nativeInputValueSetter.call(ta, draft);
      ta.dispatchEvent(new Event('input', { bubbles: true }));
    }

    // Visual cue — colour-coded by AI confidence
    const borderColor = confidence === 'high'   ? '#10b981'  // green
                      : confidence === 'medium' ? '#f59e0b'  // amber
                      :                           '#f87171'; // red/low
    
    ta.style.cssText += `
      border: 2px solid ${borderColor} !important;
      background-color: rgba(168, 85, 247, 0.04) !important;
      transition: border-color 0.3s ease;
    `;

    // Add a small floating badge so the user knows AI wrote this
    injectBadge(ta, confidence);

    filledCount++;
  });

  return { count: filledCount, failed: failedIds };
}


// ─────────────────────────────────────────────────────────────────────────────
// injectBadge — floating "AI Draft" label above the textarea
// ─────────────────────────────────────────────────────────────────────────────
function injectBadge(ta, confidence) {
  // Remove any existing badge for this element
  const existingBadge = ta.parentElement?.querySelector('.scholarscope-badge');
  if (existingBadge) existingBadge.remove();

  const badge = document.createElement('div');
  badge.className = 'scholarscope-badge';
  badge.setAttribute('data-scholarscope-badge', 'true');

  const confidenceLabel = { high: 'High', medium: 'Medium', low: 'Low' }[confidence] || '?';
  badge.innerHTML = `
    <span style="font-size:12px">✨</span>
    AI Draft · Confidence: <strong>${confidenceLabel}</strong>
    &nbsp;·&nbsp;
    <span 
      style="cursor:pointer;text-decoration:underline" 
      onclick="this.closest('[data-scholarscope-badge]').remove(); 
               document.querySelector('textarea[data-scholarscope-id=&quot;${ta.getAttribute('data-scholarscope-id')}&quot;]').value = '';
               document.querySelector('textarea[data-scholarscope-id=&quot;${ta.getAttribute('data-scholarscope-id')}&quot;]').dispatchEvent(new Event('input',{bubbles:true}));"
    >Clear</span>
  `;

  badge.style.cssText = `
    position: relative;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: rgba(168,85,247,0.1);
    border: 1px solid rgba(168,85,247,0.35);
    border-radius: 4px;
    color: #7c3aed;
    font-family: system-ui, sans-serif;
    font-size: 11px;
    padding: 3px 8px;
    margin-bottom: 4px;
    z-index: 9999;
  `;

  ta.insertAdjacentElement('beforebegin', badge);
}


// ─────────────────────────────────────────────────────────────────────────────
// clearHighlights — remove all ScholarScope visual decorations
// ─────────────────────────────────────────────────────────────────────────────
function clearHighlights() {
  document.querySelectorAll('.scholarscope-badge').forEach(el => el.remove());
  document.querySelectorAll('textarea[data-scholarscope-id]').forEach(ta => {
    ta.style.border = '';
    ta.style.backgroundColor = '';
    ta.removeAttribute('data-scholarscope-id');
  });
}


// Utils
function isVisible(el) {
  const style = getComputedStyle(el);
  return (
    style.display !== 'none' &&
    style.visibility !== 'hidden' &&
    style.opacity !== '0' &&
    el.offsetParent !== null
  );
}

function cleanText(str) {
  return str.replace(/\s+/g, ' ').replace(/[\r\n]+/g, ' ').trim();
}
