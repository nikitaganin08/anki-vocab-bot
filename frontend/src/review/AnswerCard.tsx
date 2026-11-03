import { useEffect } from "react";

import type { Card, ReviewPrompt } from "../api/types";
import { GradeGrid } from "./GradeGrid";
import { CardDetails, SpeakerButton } from "./IntroCard";
import { SentencePractice } from "./SentencePractice";
import type { CheckedAnswer } from "./useReviewSession";

const VERDICT_LABELS: Record<string, string> = {
  correct: "Correct",
  typo: "Typo",
  form: "Wrong form",
  wrong: "Wrong",
};

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
  onGrade: (rating: number) => void;
}

export function AnswerCard({ card, prompt, answer, busy, onGrade }: AnswerCardProps): JSX.Element {
  const { typed, result } = answer;
  // The sentence that was asked, with the gap filled in: one of the card's usage chunks.
  const phrase = prompt.kind === "chunk" ? prompt.masked.replace("___", result.expected) : null;

  // Keys 1-4 grade like the buttons; the picked rating is also focused, so Enter takes it.
  useEffect(() => {
    const onKey = (event: KeyboardEvent): void => {
      const rating = Number(event.key);
      const target = event.target instanceof Element ? event.target : null;
      // Digits typed into the sentence box or a dialog are not grades.
      const typing = target?.closest("[role=dialog], textarea, input") != null;
      if (!busy && !typing && rating >= 1 && rating <= 4 && !event.metaKey && !event.ctrlKey && !event.altKey) {
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
      </div>
      <div className="review-sentence-row">
        <p className="review-sentence">
          {before}
          <mark className={`verdict-hl verdict-hl-${tone}`}>{result.expected}</mark>
          {after}
        </p>
        {phrase ? <SpeakerButton card={card} phrase={phrase} /> : null}
      </div>
    </div>
  );

  return (
    <section className="review-screen">
      <CardDetails card={card} lead={lead} />

      <div className="review-actions">
        <SentencePractice
          key={card.id}
          cardId={card.id}
          word={card.canonical_text}
          result={result}
          busy={busy}
          onGrade={onGrade}
        />
        <GradeGrid result={result} busy={busy} autoFocus onGrade={onGrade} />
      </div>
    </section>
  );
}
