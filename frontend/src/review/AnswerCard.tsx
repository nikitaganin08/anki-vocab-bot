import { useEffect } from "react";

import type { Card, ReviewPrompt } from "../api/types";
import { CardDetails, SpeakerButton } from "./IntroCard";
import type { CheckedAnswer } from "./useReviewSession";

const VERDICT_LABELS: Record<string, string> = {
  correct: "Correct",
  typo: "Typo",
  form: "Wrong form",
  wrong: "Wrong",
};

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
}

export function AnswerCard({ card, prompt, answer, busy, onGrade }: AnswerCardProps): JSX.Element {
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

  const empty = typed.trim() === "";
  const tone = result.verdict === "correct" ? "ok" : result.verdict === "typo" || result.verdict === "form" ? "warn" : "bad";
  const label = empty ? "No answer" : VERDICT_LABELS[result.verdict];
  const [before, after] = prompt.kind === "chunk" ? prompt.masked.split("___") : ["", ""];

  const lead = (
    <div className="review-lead">
      <div className="review-lead-head">
        <span className={`verdict-chip verdict-${tone}`}>{label}</span>
        {result.verdict === "correct" || empty ? null : (
          <span className="review-typed">
            {result.verdict === "wrong" ? (
              <s className="verdict-typed">{typed}</s>
            ) : result.verdict === "typo" ? (
              <Diff text={typed} other={result.expected} />
            ) : (
              typed
            )}
          </span>
        )}
        {phrase ? <SpeakerButton card={card} phrase={phrase} /> : null}
      </div>
      <p className="review-sentence">
        {before}
        <mark className={`verdict-hl verdict-hl-${tone}`}>{result.expected}</mark>
        {after}
      </p>
    </div>
  );

  return (
    <section className="review-screen">
      <CardDetails card={card} lead={lead} />

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
    </section>
  );
}
