const url = document.getElementById("url");
const token = document.getElementById("token");
const status = document.getElementById("status");

chrome.storage.sync.get(["url", "token"]).then((saved) => {
  url.value = saved.url || "";
  token.value = saved.token || "";
});

document.getElementById("save").addEventListener("click", async () => {
  const origin = new URL(url.value).origin;
  // The API address is the only site the extension may talk to.
  const granted = await chrome.permissions.request({ origins: [`${origin}/*`] });
  if (!granted) {
    status.textContent = "Access to the address was not granted";
    return;
  }
  await chrome.storage.sync.set({ url: url.value.trim(), token: token.value.trim() });
  status.textContent = "Saved";
});
