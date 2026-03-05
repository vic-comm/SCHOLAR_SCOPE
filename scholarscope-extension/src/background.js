// src/background.js 

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