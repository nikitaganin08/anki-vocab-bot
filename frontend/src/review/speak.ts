import { getCardAudio } from "../api/client";

// Server audio (Google TTS via the backend) when configured, else device speech. Telegram Desktop
// and the Android WebView may lack speechSynthesis: without both the speaker button is hidden.
export function canSpeak(): boolean {
  return "speechSynthesis" in window;
}

export function speak(text: string): void {
  if (!canSpeak()) {
    return;
  }
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "en-US";
  // Empty until the device has loaded its voices; then lang alone picks one.
  const voices = window.speechSynthesis.getVoices();
  const voice =
    voices.find((v) => /^en[-_]US$/i.test(v.lang)) ?? voices.find((v) => /^en([-_]|$)/i.test(v.lang));
  if (voice) {
    utterance.voice = voice;
  }
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utterance);
}

// One request per card per page load: the promise is kept, so double taps share it and a failed
// card goes straight to device speech. Object URLs live until the page closes.
const loading = new Map<number, Promise<string>>();
const ready = new Map<number, string>();

function loadAudio(cardId: number): Promise<string> {
  let url = loading.get(cardId);
  if (!url) {
    url = getCardAudio(cardId).then((blob) => {
      const objectUrl = URL.createObjectURL(blob);
      ready.set(cardId, objectUrl);
      return objectUrl;
    });
    loading.set(cardId, url);
  }
  return url;
}

export function playPronunciation(
  card: { id: number; canonical_text: string },
  ttsEnabled: boolean,
): void {
  if (!ttsEnabled) {
    speak(card.canonical_text);
    return;
  }
  // A loaded clip plays synchronously, inside the tap: iOS may refuse play() after an await.
  const url = ready.get(card.id);
  const playing = url ? new Audio(url).play() : loadAudio(card.id).then((u) => new Audio(u).play());
  playing.catch(() => speak(card.canonical_text));
}
