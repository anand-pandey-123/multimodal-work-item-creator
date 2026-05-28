chrome.runtime.onMessage.addListener((request, _sender, sendResponse) => {
  if (request.action === "captureTab") {
    chrome.tabs.captureVisibleTab(
      null,
      { format: "png", quality: 90 },
      (dataUrl) => {
        if (chrome.runtime.lastError) {
          sendResponse({ error: chrome.runtime.lastError.message });
          return;
        }
        sendResponse({ screenshot: dataUrl });
      }
    );
    return true;
  }
});
