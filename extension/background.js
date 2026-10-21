const MENU_ID = "wordloop-add";

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({ id: MENU_ID, title: "Add “%s” to Wordloop", contexts: ["selection"] });
});

function notify(message) {
  chrome.notifications.create({
    type: "basic",
    iconUrl: "icon.png",
    title: "Wordloop",
    message,
  });
}

function describe(result) {
  switch (result.status) {
    case "created":
      return `Added: ${result.canonical_text}`;
    case "duplicate_source":
    case "duplicate_canonical":
      return `Already in your dictionary: ${result.canonical_text}`;
    default:
      return result.message || "Could not add this";
  }
}

chrome.contextMenus.onClicked.addListener(async (info) => {
  const { url, token } = await chrome.storage.sync.get(["url", "token"]);
  if (!url || !token) {
    chrome.runtime.openOptionsPage();
    return;
  }
  try {
    const response = await fetch(`${url.replace(/\/$/, "")}/api/clip`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ text: info.selectionText }),
    });
    if (!response.ok) {
      const detail = (await response.json().catch(() => ({}))).detail;
      notify(typeof detail === "string" ? detail : `Error ${response.status}`);
      return;
    }
    notify(describe(await response.json()));
  } catch {
    notify("Server unreachable");
  }
});
