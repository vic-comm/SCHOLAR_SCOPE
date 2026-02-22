// // src/background/index.js

// // 1. Create Context Menus when extension is installed
// chrome.runtime.onInstalled.addListener(() => {
//   // Parent Menu Item
//   chrome.contextMenus.create({
//     id: "scholarscope-root",
//     title: "ScholarScope",
//     contexts: ["selection"] // Only show when text is highlighted
//   });

//   // Child: Eligibility
//   chrome.contextMenus.create({
//     parentId: "scholarscope-root",
//     id: "add_eligibility",
//     title: "Add to Eligibility",
//     contexts: ["selection"]
//   });

//   // Child: Requirements
//   chrome.contextMenus.create({
//     parentId: "scholarscope-root",
//     id: "add_requirements",
//     title: "Add to Requirements",
//     contexts: ["selection"]
//   });
  
//   // Child: Benefits/Reward
//   chrome.contextMenus.create({
//     parentId: "scholarscope-root",
//     id: "set_reward",
//     title: "Set Reward Amount",
//     contexts: ["selection"]
//   });
// });

// // 2. Listen for Clicks on our Menu Items
// chrome.contextMenus.onClicked.addListener((info, tab) => {
//   const { menuItemId, selectionText } = info;

//   // Map menu IDs to our data fields
//   if (menuItemId === "add_eligibility") {
//     appendToDraft("eligibility", selectionText);
//   } else if (menuItemId === "add_requirements") {
//     appendToDraft("requirements", selectionText);
//   } else if (menuItemId === "set_reward") {
//     // Reward is usually a single value, so we overwrite instead of append
//     updateDraftField("reward", selectionText);
//   }
// });

// // 3. Helper: Append text to existing field in Storage (The "Basket")
// function appendToDraft(key, text) {
//   chrome.storage.local.get(['draft'], (result) => {
//     const currentDraft = result.draft || {};
//     const previousText = currentDraft[key] || "";
    
//     // Add a bullet point if there is already text
//     const newText = previousText ? `${previousText}\n• ${text}` : `• ${text}`;
    
//     const updatedDraft = { ...currentDraft, [key]: newText };
//     saveDraft(updatedDraft);
//   });
// }

// // 4. Helper: Overwrite a field (like Reward or Deadline)
// function updateDraftField(key, value) {
//   chrome.storage.local.get(['draft'], (result) => {
//     const currentDraft = result.draft || {};
//     const updatedDraft = { ...currentDraft, [key]: value };
//     saveDraft(updatedDraft);
//   });
// }

// // 5. Save to Chrome Storage & Flash Badge
// function saveDraft(draft) {
//   chrome.storage.local.set({ draft }, () => {
//     // Show a little "1" on the icon to indicate data is saved
//     chrome.action.setBadgeText({ text: "+" });
//     chrome.action.setBadgeBackgroundColor({ color: "#22c55e" }); // Green
    
//     // Clear badge after 1.5 seconds
//     setTimeout(() => {
//       chrome.action.setBadgeText({ text: "" });
//     }, 1500);
//   });
// }

// src/background/index.js

// ── Context Menus on install ──────────────────────────────────────────────────
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({ id: 'scholarscope-root', title: 'ScholarScope', contexts: ['selection'] });
  chrome.contextMenus.create({ parentId: 'scholarscope-root', id: 'add_eligibility',  title: '+ Add to Eligibility',  contexts: ['selection'] });
  chrome.contextMenus.create({ parentId: 'scholarscope-root', id: 'add_requirements', title: '+ Add to Requirements', contexts: ['selection'] });
  chrome.contextMenus.create({ parentId: 'scholarscope-root', id: 'set_reward',       title: 'Set as Reward Amount', contexts: ['selection'] });
  chrome.contextMenus.create({ parentId: 'scholarscope-root', id: 'set_deadline',     title: 'Set as Deadline',      contexts: ['selection'] });
});

// ── Context menu clicks ───────────────────────────────────────────────────────
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

// ── Draft helpers ─────────────────────────────────────────────────────────────
function appendToDraft(key, text) {
  chrome.storage.local.get(['draft'], (r) => {
    const draft = r.draft || {};
    const prev  = draft[key] || '';
    draft[key]  = prev ? `${prev}\n• ${text}` : `• ${text}`;
    saveDraft(draft);
  });
}

function setDraftField(key, value) {
  chrome.storage.local.get(['draft'], (r) => {
    const draft = r.draft || {};
    draft[key]  = value;
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

// ── Token sync messages from web-app ─────────────────────────────────────────
chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg.action === 'SYNC_TOKEN' && msg.token) {
    chrome.storage.local.set({ auth_token: msg.token });
    sendResponse({ ok: true });
  }
  if (msg.action === 'CLEAR_TOKEN') {
    chrome.storage.local.remove('auth_token');
    sendResponse({ ok: true });
  }
  return false;
});