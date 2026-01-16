// src/background/index.js

// 1. Create Context Menus when extension is installed
chrome.runtime.onInstalled.addListener(() => {
  // Parent Menu Item
  chrome.contextMenus.create({
    id: "scholarscope-root",
    title: "ScholarScope",
    contexts: ["selection"] // Only show when text is highlighted
  });

  // Child: Eligibility
  chrome.contextMenus.create({
    parentId: "scholarscope-root",
    id: "add_eligibility",
    title: "Add to Eligibility",
    contexts: ["selection"]
  });

  // Child: Requirements
  chrome.contextMenus.create({
    parentId: "scholarscope-root",
    id: "add_requirements",
    title: "Add to Requirements",
    contexts: ["selection"]
  });
  
  // Child: Benefits/Reward
  chrome.contextMenus.create({
    parentId: "scholarscope-root",
    id: "set_reward",
    title: "Set Reward Amount",
    contexts: ["selection"]
  });
});

// 2. Listen for Clicks on our Menu Items
chrome.contextMenus.onClicked.addListener((info, tab) => {
  const { menuItemId, selectionText } = info;

  // Map menu IDs to our data fields
  if (menuItemId === "add_eligibility") {
    appendToDraft("eligibility", selectionText);
  } else if (menuItemId === "add_requirements") {
    appendToDraft("requirements", selectionText);
  } else if (menuItemId === "set_reward") {
    // Reward is usually a single value, so we overwrite instead of append
    updateDraftField("reward", selectionText);
  }
});

// 3. Helper: Append text to existing field in Storage (The "Basket")
function appendToDraft(key, text) {
  chrome.storage.local.get(['draft'], (result) => {
    const currentDraft = result.draft || {};
    const previousText = currentDraft[key] || "";
    
    // Add a bullet point if there is already text
    const newText = previousText ? `${previousText}\n• ${text}` : `• ${text}`;
    
    const updatedDraft = { ...currentDraft, [key]: newText };
    saveDraft(updatedDraft);
  });
}

// 4. Helper: Overwrite a field (like Reward or Deadline)
function updateDraftField(key, value) {
  chrome.storage.local.get(['draft'], (result) => {
    const currentDraft = result.draft || {};
    const updatedDraft = { ...currentDraft, [key]: value };
    saveDraft(updatedDraft);
  });
}

// 5. Save to Chrome Storage & Flash Badge
function saveDraft(draft) {
  chrome.storage.local.set({ draft }, () => {
    // Show a little "1" on the icon to indicate data is saved
    chrome.action.setBadgeText({ text: "+" });
    chrome.action.setBadgeBackgroundColor({ color: "#22c55e" }); // Green
    
    // Clear badge after 1.5 seconds
    setTimeout(() => {
      chrome.action.setBadgeText({ text: "" });
    }, 1500);
  });
}