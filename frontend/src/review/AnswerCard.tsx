import type { Card } from "../api/types";
import { CardDetails } from "./IntroCard";
import type { CheckedAnswer } from "./useReviewSession";

const GRADES = [
  { rating: 1, label: "Снова" },
  { rating: 2, label: "Трудно" },
  { rating: 3, label: "Хорошо" },
  { rating: 4, label: "Легко" },
];

// Round first, then pick the unit: 3570 s is "1 ч", not "60 м".
export function formatInterval(seconds: number): string {
  if (seconds < 60) {
    return "<1 м";
  }
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) {
    return `${minutes} м`;
  }
  const hours = Math.round(seconds / 3600);
  if (hours < 24) {
    return `${hours} ч`;
  }
  return `${Math.round(seconds / 86400)} д`;
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
  answer: CheckedAnswer;
  busy: boolean;
  onGrade: (rating: number, overridden?: boolean) => void;
}

export function AnswerCard({ card, answer, busy, onGrade }: AnswerCardProps): JSX.Element {
  const { typed, result } = answer;

  return (
    <section className="review-screen">
      {result.verdict === "correct" ? (
        <p className="review-verdict">✓ верно</p>
      ) : (
        <p className="review-verdict">
          Ты: <Diff text={typed} other={result.expected} /> → верно:{" "}
          <Diff text={result.expected} other={typed} />
          {result.verdict === "typo" ? <span className="info-chip">опечатка</span> : null}
        </p>
      )}

      <CardDetails card={card} full />

      {result.verdict === "wrong" ? (
        <button type="button" className="link-button" disabled={busy} onClick={() => onGrade(3, true)}>
          Мой ответ верный
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
      <p className="section-label">Оценка выбрана автоматически, можно поменять</p>
    </section>
  );
}
