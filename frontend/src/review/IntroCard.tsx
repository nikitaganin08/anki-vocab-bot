import { useEffect } from "react";

import type { Card } from "../api/types";
import { prefetchAudio, pronounce } from "./speak";

// Tabler "volume" outline icon (MIT), 24x24.
const SPEAKER_PATHS = [
  "M15 8a5 5 0 0 1 0 8",
  "M17.7 5a9 9 0 0 1 0 14",
  "M6 15H4a1 1 0 0 1-1-1v-4a1 1 0 0 1 1-1h2l3.5-4.5A.8.8 0 0 1 11 5v14a.8.8 0 0 1-1.5.5L6 15",
];

// The full card, shared by the intro and the back side. Audio is downloaded when the card
// shows but plays only on tap.
export function CardDetails({ card }: { card: Card }): JSX.Element {
  useEffect(() => prefetchAudio(card.id), [card.id]);

  return (
    <div className="surface-panel review-card">
      <div className="review-word">
        <h2>{card.canonical_text}</h2>
        <button
          type="button"
          className="icon-button"
          aria-label="Play pronunciation"
          onClick={() => void pronounce(card.id, card.canonical_text)}
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            {SPEAKER_PATHS.map((d) => (
              <path key={d} d={d} />
            ))}
          </svg>
        </button>
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

export function IntroCard({ card, onRemember }: { card: Card; onRemember: () => void }): JSX.Element {
  return (
    <section className="review-screen">
      <span className="info-chip">New word</span>
      <CardDetails card={card} />
      <button type="button" className="primary-button" autoFocus onClick={onRemember}>
        Got it
      </button>
    </section>
  );
}
