// Toolbar-button click: figure out which marketplace the active tab is on and
// inject the matching script (the exact same logic as the site's bookmarklets,
// just bundled here so it works without a bookmarks bar and passes Chrome's
// no-remote-code rule). depop.js / vinted.js are generated from app.py's
// bookmarklet templates - keep them in sync.
const HOMEPAGE = "https://crosslister.onrender.com/";

chrome.action.onClicked.addListener(async (tab) => {
  const url = tab.url || "";
  let file = null;
  if (/^https:\/\/www\.depop\.com\//.test(url)) file = "depop.js";
  else if (/^https:\/\/www\.vinted\.com\//.test(url)) file = "vinted.js";

  if (!file) {
    // Not on a supported page - open the instructions rather than fail silently.
    chrome.tabs.create({ url: HOMEPAGE });
    return;
  }

  try {
    await chrome.scripting.executeScript({ target: { tabId: tab.id }, files: [file] });
  } catch (e) {
    chrome.tabs.create({ url: HOMEPAGE });
  }
});
