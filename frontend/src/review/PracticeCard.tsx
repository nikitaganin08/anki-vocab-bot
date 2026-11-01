import type { Card } from "../api/types";
import { CardDetails } from "./IntroCard";
import { SentencePractice } from "./SentencePractice";

// Shown right after a grade: the card's back side with an optional sentence to write.
export function PracticeCard({ card, onNext }: { card: Card; onNext: () => void }): JSX.Element {
  return (
    <section className="review-screen">
      <CardDetails card={card} />
      <SentencePractice cardId={card.id} />
      <button type="button" className="primary-button" onClick={onNext}>
        Next
      </button>
    </section>
  );
}
