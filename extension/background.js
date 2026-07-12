importScripts("config.js");

const ENDPOINT = self.IDEABUCKET_ENDPOINT || "http://127.0.0.1:8787/capture";
const CAPTURE_TOKEN = self.IDEABUCKET_CAPTURE_TOKEN || "";

chrome.action.onClicked.addListener(async (tab) => {
  const setBadge = (text, color) => {
    chrome.action.setBadgeText({ text, tabId: tab.id });
    chrome.action.setBadgeBackgroundColor({ color, tabId: tab.id });
    setTimeout(() => chrome.action.setBadgeText({ text: "", tabId: tab.id }), 3000);
  };

  if (!tab.url || !tab.url.startsWith("http")) {
    setBadge("✗", "#ef4444");
    return;
  }

  try {
    const res = await fetch(ENDPOINT, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Ideabucket-Token": CAPTURE_TOKEN,
      },
      body: JSON.stringify({ url: tab.url }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    setBadge(data.ok ? "✓" : "✗", data.ok ? "#22c55e" : "#ef4444");
  } catch (e) {
    // bot 沒開、token 不一致或本機端口設定錯誤
    setBadge("✗", "#ef4444");
  }
});
