import { useEffect, useRef, useState } from "react";

import { transcribeSentence } from "../api/client";

// Speak instead of typing: tap to record, tap again to stop; the backend turns the audio into
// text (nothing is kept) and the text goes into the sentence box, where it can still be edited.
// Hidden where the browser cannot record.
export function canDictate(): boolean {
  return Boolean(navigator.mediaDevices?.getUserMedia) && typeof MediaRecorder !== "undefined";
}

interface DictateButtonProps {
  cardId: number;
  onText: (text: string) => void;
}

export function DictateButton({ cardId, onText }: DictateButtonProps): JSX.Element {
  const [state, setState] = useState<"idle" | "recording" | "sending">("idle");
  const [error, setError] = useState<string | null>(null);
  const recorder = useRef<MediaRecorder | null>(null);

  // Leaving the sheet mid-recording releases the microphone.
  useEffect(() => () => recorder.current?.stream.getTracks().forEach((track) => track.stop()), []);

  async function start(): Promise<void> {
    setError(null);
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      setError("No access to the microphone.");
      return;
    }
    const rec = new MediaRecorder(stream);
    const chunks: Blob[] = [];
    rec.ondataavailable = (event) => chunks.push(event.data);
    rec.onstop = async () => {
      stream.getTracks().forEach((track) => track.stop());
      recorder.current = null;
      setState("sending");
      try {
        onText(await transcribeSentence(cardId, new Blob(chunks, { type: rec.mimeType })));
      } catch (err) {
        setError((err as Error).message);
      }
      setState("idle");
    };
    rec.start();
    recorder.current = rec;
    setState("recording");
  }

  return (
    <>
      <button
        type="button"
        className="secondary-button"
        disabled={state === "sending"}
        onClick={() => (recorder.current ? recorder.current.stop() : void start())}
      >
        {state === "recording" ? "■ Stop" : state === "sending" ? "Listening…" : "🎤 Speak"}
      </button>
      {error ? <p className="batch-message batch-message-error">{error}</p> : null}
    </>
  );
}
