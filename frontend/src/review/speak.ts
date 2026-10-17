// Device TTS only, no server audio. Telegram Desktop and the Android WebView may lack it:
// the speaker button is hidden then.
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
