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

// One request per card per page load: the promise is kept, so double taps share it. Object URLs
// live until the page closes. Keyed by id + word, since ids can be reused after a delete.
const loading = new Map<string, Promise<string>>();
const ready = new Map<string, string>();

function loadAudio(key: string, cardId: number, text: string, phrase: boolean): Promise<string> {
  let url = loading.get(key);
  if (!url) {
    url = getCardAudio(cardId, text, phrase ? text : undefined).then((blob) => {
      const objectUrl = URL.createObjectURL(blob);
      ready.set(key, objectUrl);
      return objectUrl;
    });
    loading.set(key, url);
    // A failed load is retried on the next tap.
    url.catch(() => loading.delete(key));
  }
  return url;
}

// The card's word, or `phrase` (one of its usage chunks or examples) when given.
export function playPronunciation(
  card: { id: number; canonical_text: string },
  ttsEnabled: boolean,
  phrase?: string,
): void {
  const text = phrase ?? card.canonical_text;
  if (!ttsEnabled) {
    speak(text);
    return;
  }
  const key = `${card.id}:${text}`;
  const url = ready.get(key);
  // A loaded clip plays synchronously, inside the tap: iOS may refuse play() after an await.
  if (url) {
    new Audio(url).play().catch(() => speak(text));
    return;
  }
  // Taps while the first load is pending would play the clip twice at once.
  if (loading.has(key)) {
    return;
  }
  loadAudio(key, card.id, text, phrase !== undefined)
    .then((u) => new Audio(u).play())
    .catch(() => speak(text));
}
