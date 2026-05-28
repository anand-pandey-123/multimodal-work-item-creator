chrome.runtime.onMessage.addListener((request, _sender, sendResponse) => {
  if (request.action === "captureScreenshot") {
    sendResponse({ status: "ok" });
  }
});
