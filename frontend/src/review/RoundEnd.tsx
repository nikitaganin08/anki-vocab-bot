import type { ReviewSummary } from "../api/types";
import { cardsLabel } from "../home/HomeView";

interface RoundEndProps {
  summary: ReviewSummary;
  // Nothing left today: "Готово на сегодня" with a single way back.
  done: boolean;
  onMore: () => void;
  onExit: () => void;
}

export function RoundEnd({ summary, done, onMore, onExit }: RoundEndProps): JSX.Element {
  if (done) {
    return (
      <section className="review-screen review-end">
        <h2>Готово на сегодня</h2>
        <p className="section-label">Завтра ~{cardsLabel(summary.forecast_tomorrow)}</p>
        <button type="button" className="primary-button" onClick={onExit}>
          Закрыть
        </button>
      </section>
    );
  }

  // Both sides count graded answers: today's answers (last heatmap cell) plus one answer per
  // card still due or new today, from the summary fetched after this round. An Again re-queues
  // the card as learning, so Y can grow during the day.
  const doneToday = summary.heatmap[summary.heatmap.length - 1] ?? 0;
  const goal = doneToday + summary.due_today + summary.new_today;
  return (
    <section className="review-screen review-end">
      <h2>✓ Раунд готов</h2>
      <p>
        Сегодня {doneToday} из {goal}
      </p>
      <progress value={doneToday} max={goal} />
      <p className="section-label">Осталось ~{summary.est_minutes} мин</p>
      <button type="button" className="primary-button" onClick={onMore}>
        Ещё раунд
      </button>
      <button type="button" className="secondary-button" onClick={onExit}>
        На сегодня хватит
      </button>
    </section>
  );
}
