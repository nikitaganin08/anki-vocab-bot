import { getCardAudio } from "../api/client";

// Card id -> object URL of the server MP3 once downloaded (kept for the page's lifetime).
const readyUrls = new Map<number, string>();
// Card id -> download in flight or done; one request per card even on double taps.
const downloads = new Map<number, Promise<string>>();

function download(cardId: number): Promise<string> {
  let url = downloads.get(cardId);
  if (url === undefined) {
    url = getCardAudio(cardId).then((blob) => {
      const objectUrl = URL.createObjectURL(blob);
      readyUrls.set(cardId, objectUrl);
      return objectUrl;
    });
    downloads.set(cardId, url);
    url.catch(() => downloads.delete(cardId));
  }
  return url;
}

function speakInBrowser(text: string): void {
  if (!("speechSynthesis" in window)) {
    return;
  }
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "en-US";
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utterance);
}

// Download (never play) when a card is shown, so a tap can start playback inside the gesture:
// iOS blocks play() that only starts after an await.
export function prefetchAudio(cardId: number): void {
  download(cardId).catch(() => undefined);
}

// Server audio (edge-tts, same voice as Anki); browser TTS when the fetch or playback fails,
// silence when there is no TTS either.
export async function pronounce(cardId: number, text: string): Promise<void> {
  try {
    const url = readyUrls.get(cardId) ?? (await download(cardId));
    await new Audio(url).play();
  } catch {
    speakInBrowser(text);
  }
}
