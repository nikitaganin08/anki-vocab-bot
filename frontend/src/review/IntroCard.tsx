import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { getSettings } from "../api/client";
import type { Card } from "../api/types";
import { DeleteCardDialog } from "../components/DeleteCardDialog";
import { canSpeak, playPronunciation } from "./speak";

// Tabler "volume" outline icon (MIT), 24x24.
const SPEAKER_PATHS = [
  "M15 8a5 5 0 0 1 0 8",
  "M17.7 5a9 9 0 0 1 0 14",
  "M6 15H4a1 1 0 0 1-1-1v-4a1 1 0 0 1 1-1h2l3.5-4.5A.8.8 0 0 1 11 5v14a.8.8 0 0 1-1.5.5L6 15",
];

// The full card, shared by the intro and the back side. Pronunciation plays only on tap.
export function CardDetails({ card }: { card: Card }): JSX.Element {
  // Shares the ["settings"] cache; until it loads (or if it fails) device speech is used.
  const { data: settings } = useQuery({
    queryKey: ["settings"],
    queryFn: getSettings,
    staleTime: Infinity,
  });
  const ttsEnabled = settings?.tts_enabled === true;
  return (
    <div className="surface-panel review-card">
      <div className="review-word">
        <h2>{card.canonical_text}</h2>
        {ttsEnabled || canSpeak() ? (
          <button
            type="button"
            className="icon-button"
            aria-label="Play pronunciation"
            onClick={() => playPronunciation(card, ttsEnabled)}
          >
            <svg viewBox="0 0 24 24" aria-hidden="true">
              {SPEAKER_PATHS.map((d) => (
                <path key={d} d={d} />
              ))}
            </svg>
          </button>
        ) : null}
        {card.transcription ? <span className="section-label">{card.transcription}</span> : null}
      </div>
      <p>{card.translation_variants.join(", ")}</p>
      {card.explanation ? <p>{card.explanation}</p> : null}
      {card.chunks.length > 0 ? (
        <section className="review-chunks">
          <h3 className="section-label">Usage</h3>
          <ul>
            {card.chunks.map((chunk) => (
              <li key={chunk.text}>
                <span>{chunk.text}</span> <span className="section-label">{chunk.translation}</span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      {card.examples[0] ? <p className="review-example">{card.examples[0]}</p> : null}
      {card.word_family.length > 0 ? (
        <ul className="review-family section-label">
          {card.word_family.map((item) => (
            <li key={item.word}>
              {item.word} ({item.part_of_speech}) — {item.translation}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

// "Delete word" under the card: for a word that should never have been added.
export function DeleteWord({ card, onDeleted }: { card: Card; onDeleted: () => void }): JSX.Element {
  const [confirming, setConfirming] = useState(false);
  return (
    <>
      <button type="button" className="link-button" onClick={() => setConfirming(true)}>
        Delete word
      </button>
      {confirming ? (
        <DeleteCardDialog card={card} onCancel={() => setConfirming(false)} onDeleted={onDeleted} />
      ) : null}
    </>
  );
}

interface IntroCardProps {
  card: Card;
  onRemember: () => void;
  onDeleted: () => void;
}

export function IntroCard({ card, onRemember, onDeleted }: IntroCardProps): JSX.Element {
  return (
    <section className="review-screen">
      <span className="info-chip">New word</span>
      <CardDetails card={card} />
      <button type="button" className="primary-button" autoFocus onClick={onRemember}>
        Got it
      </button>
      <DeleteWord card={card} onDeleted={onDeleted} />
    </section>
  );
}
