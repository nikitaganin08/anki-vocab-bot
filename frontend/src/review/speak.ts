import { getCardAudio } from "../api/client";

// Card id -> object URL of the server MP3, kept for the page's lifetime.
const audioUrls = new Map<number, string>();

function speakInBrowser(text: string): void {
  if (!("speechSynthesis" in window)) {
    return;
  }
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "en-US";
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utterance);
}

// Server audio (edge-tts, same voice as Anki); browser TTS when the fetch or playback fails,
// silence when there is no TTS either.
export async function pronounce(cardId: number, text: string): Promise<void> {
  try {
    let url = audioUrls.get(cardId);
    if (url === undefined) {
      url = URL.createObjectURL(await getCardAudio(cardId));
      audioUrls.set(cardId, url);
    }
    await new Audio(url).play();
  } catch {
    speakInBrowser(text);
  }
}
