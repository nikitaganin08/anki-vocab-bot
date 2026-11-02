import { useMutation } from "@tanstack/react-query";
import { useState } from "react";

import { checkSentence } from "../api/client";
import { Sheet } from "../components/Sheet";
import { diffSentence } from "./sentenceDiff";

// Optional extra on the back side: a button opens a sheet to write a sentence with the word and
// get feedback. The card stays behind it; it never changes the grade or the schedule.
export function SentencePractice({ cardId, word }: { cardId: number; word: string }): JSX.Element {
  const [open, setOpen] = useState(false);
  const [sentence, setSentence] = useState("");
  const mutation = useMutation({ mutationFn: () => checkSentence(cardId, sentence.trim()) });

  const feedback = mutation.data;
  const diff = feedback?.corrected ? diffSentence(sentence, feedback.corrected) : null;
  return (
    <>
      <button type="button" className="secondary-button practice-button" onClick={() => setOpen(true)}>
        Test yourself: use it in a sentence
      </button>
      {open ? (
        <Sheet label="Use it in a sentence" onClose={() => setOpen(false)}>
          <h2 className="sheet-title">{word}</h2>
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
            <button type="submit" className="primary-button" disabled={mutation.isPending || !sentence.trim()}>
              {mutation.isPending ? "Checking…" : "Check sentence"}
            </button>
            {mutation.isError ? <p className="batch-message batch-message-error">{mutation.error.message}</p> : null}
            {feedback ? (
              <div className="sentence-feedback">
                <span className={`verdict-chip ${feedback.ok ? "verdict-ok" : "verdict-warn"}`}>
                  {feedback.ok ? "Looks good" : "Needs a fix"}
                </span>
                {diff ? (
                  <p className="review-sentence">
                    {diff.corrected.map((word, index) => (
                      <span key={index}>
                        {index ? " " : ""}
                        {word.changed ? <mark className="sentence-fix">{word.text}</mark> : word.text}
                      </span>
                    ))}
                  </p>
                ) : null}
                {diff?.removed.length ? (
                  <p className="sentence-was">
                    Instead of: {diff.removed.map((part, index) => (
                      <span key={index}>
                        {index ? " … " : ""}
                        <s>{part}</s>
                      </span>
                    ))}
                  </p>
                ) : null}
                <p className="sentence-comment">{feedback.comment}</p>
              </div>
            ) : null}
          </form>
          <div className="sheet-actions">
            <button type="button" className="secondary-button" onClick={() => setOpen(false)}>
              Close
            </button>
          </div>
        </Sheet>
      ) : null}
    </>
  );
}
