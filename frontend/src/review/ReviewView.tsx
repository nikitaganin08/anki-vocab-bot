import { ErrorState, LoadingState } from "../components/PageState";
import type { ReviewMode } from "../home/HomeView";
import { AnswerCard } from "./AnswerCard";
import { IntroCard } from "./IntroCard";
import { QuestionCard } from "./QuestionCard";
import { RoundEnd } from "./RoundEnd";
import { useReviewSession } from "./useReviewSession";

interface ReviewViewProps {
  mode: ReviewMode;
  onExit: () => void;
}

export function ReviewView({ mode, onExit }: ReviewViewProps): JSX.Element | null {
  const session = useReviewSession(mode);
  const { item, summary } = session;

  switch (session.phase) {
    case "loading":
      return <LoadingState title="Review" message="Loading cards…" />;
    case "error":
      return <ErrorState error={session.error} onRetry={session.retry} />;
    case "intro":
      return <IntroCard card={item.card} onRemember={session.remember} onDeleted={() => void session.removeCard()} />;
    case "question":
      return (
        <QuestionCard
          item={item}
          round={session.round}
          estMinutes={summary?.est_minutes ?? null}
          busy={session.busy}
          onCheck={(typed, hintUsed) => void session.check(typed, hintUsed)}
        />
      );
    case "answer":
      return session.answer ? (
        <AnswerCard
          card={item.card}
          prompt={item.prompt}
          answer={session.answer}
          busy={session.busy}
          onGrade={(rating, overridden) => void session.grade(rating, overridden)}
        />
      ) : null;
    case "roundEnd":
    case "done":
      return summary ? (
        <RoundEnd summary={summary} done={session.phase === "done"} onMore={session.nextRound} onExit={onExit} />
      ) : null;
  }
}
