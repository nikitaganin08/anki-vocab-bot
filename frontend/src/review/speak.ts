// Browser TTS only; Telegram Desktop/web may lack it, then the audio button is hidden.
export function canSpeak(): boolean {
  return "speechSynthesis" in window;
}

export function speak(text: string): void {
  if (!canSpeak()) {
    return;
  }
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "en-US";
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utterance);
}
