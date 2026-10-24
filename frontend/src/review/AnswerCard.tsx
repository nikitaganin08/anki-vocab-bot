import { useEffect } from "react";

import type { Card, ReviewPrompt } from "../api/types";
import { CardDetails, DeleteWord, SpeakerButton } from "./IntroCard";
import type { CheckedAnswer } from "./useReviewSession";

const GRADES = [
  { rating: 1, label: "Again" },
  { rating: 2, label: "Hard" },
  { rating: 3, label: "Good" },
  { rating: 4, label: "Easy" },
];

// Round first, then pick the unit: 3570 s is "1h", not "60m".
export function formatInterval(seconds: number): string {
  if (seconds < 60) {
    return "<1m";
  }
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) {
    return `${minutes}m`;
  }
  const hours = Math.round(seconds / 3600);
  if (hours < 24) {
    return `${hours}h`;
  }
  return `${Math.round(seconds / 86400)}d`;
}

// Marks the part between the common prefix and suffix: enough to show where the slip is.
function Diff({ text, other }: { text: string; other: string }): JSX.Element {
  let start = 0;
  while (start < text.length && start < other.length && text[start] === other[start]) {
    start += 1;
  }
  let tail = 0;
  while (
    tail < text.length - start &&
    tail < other.length - start &&
    text[text.length - 1 - tail] === other[other.length - 1 - tail]
  ) {
    tail += 1;
  }
  const end = text.length - tail;
  return (
    <span>
      {text.slice(0, start)}
      <mark>{text.slice(start, end)}</mark>
      {text.slice(end)}
    </span>
  );
}

interface AnswerCardProps {
  card: Card;
  prompt: ReviewPrompt;
  answer: CheckedAnswer;
  busy: boolean;
  onGrade: (rating: number, overridden?: boolean) => void;
  onDeleted: () => void;
}

export function AnswerCard({ card, prompt, answer, busy, onGrade, onDeleted }: AnswerCardProps): JSX.Element {
  const { typed, result } = answer;
  // The sentence that was asked, with the gap filled in: one of the card's usage chunks.
  const phrase = prompt.kind === "chunk" ? prompt.masked.replace("___", result.expected) : null;

  // Keys 1-4 grade like the buttons; the picked rating is also focused, so Enter takes it.
  useEffect(() => {
    const onKey = (event: KeyboardEvent): void => {
      const rating = Number(event.key);
      const inDialog = event.target instanceof Element && event.target.closest("[role=dialog]");
      if (!busy && !inDialog && rating >= 1 && rating <= 4 && !event.metaKey && !event.ctrlKey && !event.altKey) {
        onGrade(rating);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [busy, onGrade]);

  return (
    <section className="review-screen">
      {result.verdict === "correct" ? (
        <p className="review-verdict">✓ correct</p>
      ) : result.verdict === "wrong" ? (
        <p className="review-verdict">
          You: <s className="verdict-typed">{typed}</s> → correct:{" "}
          <span className="verdict-expected">{result.expected}</span>
        </p>
      ) : result.verdict === "form" ? (
        <p className="review-verdict">
          You: {typed} → here: <span className="verdict-expected">{result.expected}</span>
          <span className="info-chip">form</span>
        </p>
      ) : (
        <p className="review-verdict">
          You: <Diff text={typed} other={result.expected} /> → correct:{" "}
          <Diff text={result.expected} other={typed} />
          <span className="info-chip">typo</span>
        </p>
      )}

      {phrase ? (
        <p className="review-phrase">
          <span>{phrase}</span>
          <SpeakerButton card={card} phrase={phrase} />
        </p>
      ) : null}

      <CardDetails card={card} />

      {result.verdict === "wrong" ? (
        <button type="button" className="link-button" disabled={busy} onClick={() => onGrade(3, true)}>
          My answer was right
        </button>
      ) : null}
      <div className="grade-grid">
        {GRADES.map(({ rating, label }) => (
          <button
            key={rating}
            type="button"
            className={rating === result.auto_rating ? "primary-button" : "secondary-button"}
            autoFocus={rating === result.auto_rating}
            disabled={busy}
            onClick={() => onGrade(rating)}
          >
            <span>{label}</span>
            <span className="grade-interval">{formatInterval(result.intervals[rating])}</span>
          </button>
        ))}
      </div>
      <p className="section-label">Rating picked automatically — you can change it</p>
      <DeleteWord key={card.id} card={card} onDeleted={onDeleted} />
    </section>
  );
}
