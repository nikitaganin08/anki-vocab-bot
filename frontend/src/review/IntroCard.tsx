import type { Card } from "../api/types";
import { canSpeak, speak } from "./speak";

// Tabler "volume" outline icon (MIT), 24x24.
const SPEAKER_PATHS = [
  "M15 8a5 5 0 0 1 0 8",
  "M17.7 5a9 9 0 0 1 0 14",
  "M6 15H4a1 1 0 0 1-1-1v-4a1 1 0 0 1 1-1h2l3.5-4.5A.8.8 0 0 1 11 5v14a.8.8 0 0 1-1.5.5L6 15",
];

// Shared by the intro (I1) and the back side; `full` adds word family and explanation.
export function CardDetails({ card, full = false }: { card: Card; full?: boolean }): JSX.Element {
  return (
    <div className="surface-panel review-card">
      <div className="review-word">
        <h2>{card.canonical_text}</h2>
        {canSpeak() ? (
          <button
            type="button"
            className="icon-button"
            aria-label="Произнести"
            onClick={() => speak(card.canonical_text)}
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
      {card.chunks.length > 0 ? (
        <section className="review-chunks">
          <h3 className="section-label">Как используется</h3>
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
      {full && card.word_family.length > 0 ? (
        <p className="section-label">
          {card.word_family
            .map((item) => `${item.word} (${item.part_of_speech}) — ${item.translation}`)
            .join(" · ")}
        </p>
      ) : null}
      {full ? <p className="review-explanation">{card.explanation}</p> : null}
    </div>
  );
}

export function IntroCard({ card, onRemember }: { card: Card; onRemember: () => void }): JSX.Element {
  return (
    <section className="review-screen">
      <span className="info-chip">Новое</span>
      <CardDetails card={card} />
      <button type="button" className="primary-button" autoFocus onClick={onRemember}>
        Запомнил
      </button>
    </section>
  );
}
