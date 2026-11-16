// [SPIKE-mic] Temporary: does microphone recording work inside the Telegram Mini App? Remove after.
import { useRef, useState } from "react";

export function MicTest(): JSX.Element {
  const [status, setStatus] = useState("");
  const [url, setUrl] = useState<string | null>(null);
  const recorder = useRef<MediaRecorder | null>(null);
  const started = useRef(0);

  async function start(): Promise<void> {
    setUrl(null);
    if (!navigator.mediaDevices?.getUserMedia) {
      setStatus("No navigator.mediaDevices.getUserMedia");
      return;
    }
    if (typeof MediaRecorder === "undefined") {
      setStatus("No MediaRecorder");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const rec = new MediaRecorder(stream);
      const chunks: Blob[] = [];
      rec.ondataavailable = (event) => chunks.push(event.data);
      rec.onstop = () => {
        stream.getTracks().forEach((track) => track.stop());
        const blob = new Blob(chunks, { type: rec.mimeType });
        const seconds = ((Date.now() - started.current) / 1000).toFixed(1);
        setStatus(`OK: ${rec.mimeType || "no mimeType"}, ${blob.size} bytes, ${seconds}s`);
        setUrl(URL.createObjectURL(blob));
        recorder.current = null;
      };
      rec.start();
      started.current = Date.now();
      recorder.current = rec;
      setStatus("Recording… tap again to stop");
    } catch (error) {
      const err = error as Error;
      setStatus(`Error: ${err.name}: ${err.message}`);
    }
  }

  return (
    <div className="sentence-practice">
      <button
        type="button"
        className="secondary-button"
        onClick={() => (recorder.current ? recorder.current.stop() : void start())}
      >
        🎤 Mic test
      </button>
      {status ? <p className="batch-message">{status}</p> : null}
      {url ? <audio controls src={url} /> : null}
    </div>
  );
}
