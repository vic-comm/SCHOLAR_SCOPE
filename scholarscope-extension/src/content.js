// src/content.js — CONTENT SCRIPT ONLY
// Injected into every page tab by manifest content_scripts.

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