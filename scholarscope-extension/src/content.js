// src/content/index.js
console.log("ScholarScope Companion Loaded");

// Listen for messages from the Popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  
  // The Popup is opening and asking: "What page is this?"
  if (request.action === "SCRAPE_METADATA") {
    sendResponse({
      title: document.title || "",
      url: window.location.href,
      // Try to find a meta description
      description: document.querySelector('meta[name="description"]')?.content || ""
    });
  }
});