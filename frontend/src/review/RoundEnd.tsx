import type { ReviewSummary } from "../api/types";
import { cardsLabel } from "../home/HomeView";

interface RoundEndProps {
  summary: ReviewSummary;
  // Nothing left today: "Done for today" with a single way back.
  done: boolean;
  onMore: () => void;
  onExit: () => void;
}

export function RoundEnd({ summary, done, onMore, onExit }: RoundEndProps): JSX.Element {
  if (done) {
    return (
      <section className="review-screen review-end">
        <h2>Done for today</h2>
        <p className="section-label">Tomorrow ~{cardsLabel(summary.forecast_tomorrow)}</p>
        <button type="button" className="primary-button" onClick={onExit}>
          Close
        </button>
      </section>
    );
  }

  // Distinct cards, same as the Home goal: done plus what is still due or new today.
  const doneToday = summary.done_today;
  const goal = doneToday + summary.due_today + summary.new_today;
  return (
    <section className="review-screen review-end">
      <h2>✓ Round complete</h2>
      <p>
        Today {doneToday} of {goal}
      </p>
      <progress value={doneToday} max={goal} />
      <p className="section-label">~{summary.est_minutes} min left</p>
      <button type="button" className="primary-button" onClick={onMore}>
        Another round
      </button>
      <button type="button" className="secondary-button" onClick={onExit}>
        Done for today
      </button>
    </section>
  );
}
