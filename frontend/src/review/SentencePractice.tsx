import { useMutation } from "@tanstack/react-query";
import { useState } from "react";

import { checkSentence } from "../api/client";

// Optional extra after a grade: write a sentence with the word and get feedback. It never
// changes the grade or the schedule.
export function SentencePractice({ cardId }: { cardId: number }): JSX.Element {
  const [sentence, setSentence] = useState("");
  const mutation = useMutation({ mutationFn: () => checkSentence(cardId, sentence.trim()) });

  const feedback = mutation.data;
  return (
    <form
      className="sentence-practice"
      onSubmit={(event) => {
        event.preventDefault();
        if (sentence.trim() && !mutation.isPending) {
          mutation.mutate();
        }
      }}
    >
      <textarea
        aria-label="Your sentence"
        placeholder="Write a sentence with this word"
        rows={2}
        maxLength={300}
        value={sentence}
        onChange={(event) => {
          setSentence(event.target.value);
          mutation.reset();
        }}
        autoFocus
        autoCorrect="off"
        spellCheck={false}
      />
      <button type="submit" className="secondary-button" disabled={mutation.isPending || !sentence.trim()}>
        {mutation.isPending ? "Checking…" : "Check sentence"}
      </button>
      {mutation.isError ? <p className="batch-message batch-message-error">{mutation.error.message}</p> : null}
      {feedback ? (
        <div className="sentence-feedback">
          <span className={`verdict-chip ${feedback.ok ? "verdict-ok" : "verdict-warn"}`}>
            {feedback.ok ? "Looks good" : "Needs a fix"}
          </span>
          {feedback.corrected ? <p className="review-sentence">{feedback.corrected}</p> : null}
          <p className="review-typed sentence-comment">{feedback.comment}</p>
        </div>
      ) : null}
    </form>
  );
}
