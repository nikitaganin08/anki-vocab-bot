import { useRef, useState } from "react";

import type { ReviewSessionItem } from "../api/types";
import type { Round } from "./useReviewSession";

interface QuestionCardProps {
  item: ReviewSessionItem;
  round: Round;
  estMinutes: number | null;
  busy: boolean;
  onCheck: (typed: string, hintUsed: boolean) => void;
}

// Cyrillic input is sent as typed: the server converts the ЙЦУКЕН layout.
export function QuestionCard({ item, round, estMinutes, busy, onCheck }: QuestionCardProps): JSX.Element {
  const [typed, setTyped] = useState("");
  const [hintUsed, setHintUsed] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const { prompt } = item;

  return (
    <form
      className="review-screen"
      onSubmit={(event) => {
        event.preventDefault();
        onCheck(typed, hintUsed);
      }}
    >
      <header className="review-progress">
        <div className="review-progress-line">
          <span>
            Раунд {round.number} · {round.graded + 1} из {round.total}
          </span>
          {estMinutes === null ? null : <span>~{estMinutes} мин</span>}
        </div>
        <progress value={round.graded} max={round.total} />
      </header>

      <section className="surface-panel review-card">
        <p className="review-masked">{prompt.masked}</p>
        {prompt.hint_translation ? <p className="section-label">{prompt.hint_translation}</p> : null}
      </section>

      <input
        ref={input}
        aria-label="Ответ"
        value={typed}
        maxLength={200}
        onChange={(event) => setTyped(event.target.value)}
        autoFocus
        autoComplete="off"
        autoCorrect="off"
        autoCapitalize="none"
        spellCheck={false}
      />
      <button
        type="button"
        className="link-button"
        onClick={() => {
          setHintUsed(true);
          // Keep typing in the answer field.
          input.current?.focus();
        }}
      >
        Что это за слово?
      </button>
      {hintUsed ? <p className="review-explanation">{item.card.explanation}</p> : null}
      <button type="submit" className="primary-button" disabled={busy}>
        Проверить
      </button>
    </form>
  );
}
