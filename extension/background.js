const ENDPOINT = "http://127.0.0.1:8787/capture";

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
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: tab.url }),
    });
    const data = await res.json();
    setBadge(data.ok ? "✓" : "✗", data.ok ? "#22c55e" : "#ef4444");
  } catch (e) {
    // bot 沒開(連不上 127.0.0.1:8787)
    setBadge("✗", "#ef4444");
  }
});
