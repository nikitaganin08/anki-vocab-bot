import { useQuery } from "@tanstack/react-query";

import { getReviewSummary } from "../api/client";
import type { ReviewSummary } from "../api/types";
import { ErrorState, LoadingState } from "../components/PageState";
import { Heatmap } from "./Heatmap";

export interface ReviewMode {
  includeBacklog?: boolean;
  // The session ends after this many graded cards ("Quick", "5 minutes").
  capCards?: number;
}

interface HomeViewProps {
  onStart: (mode: ReviewMode) => void;
}

export function cardsLabel(count: number): string {
  return `${count} ${count === 1 ? "card" : "cards"}`;
}

// "5 minutes": as many cards as fit in 5 minutes at today's pace, at least 5.
function fiveMinuteCap(summary: ReviewSummary): number {
  const perCard = summary.est_minutes / Math.max(summary.due_today + summary.new_today, 1);
  return perCard > 0 ? Math.max(5, Math.ceil(5 / perCard)) : 5;
}

function GoalCard({ summary, onStart }: { summary: ReviewSummary } & HomeViewProps): JSX.Element {
  const left = summary.due_today + summary.new_today;
  const total = summary.done_today + left;
  return (
    <section className="surface-panel home-card">
      {total === 0 ? (
        <h2>Done for today</h2>
      ) : (
        <>
          <h2>
            {summary.done_today} of {total} done today
          </h2>
          <progress aria-label="Today's progress" value={summary.done_today} max={total} />
          <div className="review-progress-line">
            <span>{left} left</span>
            <span>~{summary.est_minutes} min</span>
          </div>
        </>
      )}
      <button type="button" className="primary-button" onClick={() => onStart({})}>
        Start
      </button>
      <button type="button" className="secondary-button" onClick={() => onStart({ capCards: 5 })}>
        Quick: 5 cards
      </button>
    </section>
  );
}

function WelcomeBack({ summary, onStart }: { summary: ReviewSummary } & HomeViewProps): JSX.Element {
  return (
    <section className="surface-panel home-card">
      <h2>Welcome back</h2>
      <p className="section-label">How about today?</p>
      <button
        type="button"
        className="primary-button"
        onClick={() => onStart({ capCards: fiveMinuteCap(summary) })}
      >
        5 minutes
      </button>
      <button type="button" className="secondary-button" onClick={() => onStart({})}>
        Regular session
      </button>
      <button
        type="button"
        className="secondary-button"
        onClick={() => onStart({ includeBacklog: true })}
      >
        All at once ({summary.due_all})
      </button>
    </section>
  );
}

export function HomeView({ onStart }: HomeViewProps): JSX.Element {
  const { data, error, refetch } = useQuery({
    queryKey: ["review-summary"],
    queryFn: getReviewSummary,
  });

  if (error) {
    return <ErrorState error={error} onRetry={() => void refetch()} />;
  }
  if (!data) {
    return <LoadingState title="Home" message="Loading today's goal…" />;
  }

  const welcomeBack = data.days_away !== null && data.days_away >= 3 && data.due_all > 0;
  const percent = (share: number): string => `${Math.round(share * 100)}%`;
  const retention = data.retention_30d === null ? "—" : percent(data.retention_30d);

  return (
    <div className="home-view">
      {welcomeBack ? (
        <WelcomeBack summary={data} onStart={onStart} />
      ) : (
        <GoalCard summary={data} onStart={onStart} />
      )}

      <div className="stat-grid">
        <section className="surface-panel stat-tile">
          <span className="section-label">Retention (30 days)</span>
          <strong>{retention}</strong>
          <span className="section-label">goal 90%</span>
          {data.hard_share_30d !== null && data.again_share_30d !== null ? (
            <span className="section-label">
              Hard {percent(data.hard_share_30d)} · Again {percent(data.again_share_30d)}
            </span>
          ) : null}
        </section>
        <section className="surface-panel stat-tile">
          <span className="section-label">Learned</span>
          <strong>{data.learned_total}</strong>
          <span className="section-label">+{data.learned_delta_7d} this week</span>
        </section>
      </div>

      <section className="surface-panel home-activity">
        <span className="section-label">Activity</span>
        <Heatmap counts={data.heatmap} />
        {data.streak_days >= 3 ? (
          <p className="section-label">
            streak {data.streak_days} days · best {data.best_streak_days}
          </p>
        ) : null}
      </section>

      <p className="section-label">
        Tomorrow ~{data.forecast_tomorrow} · week ~{data.forecast_week_avg}/day
      </p>
      {data.backlog > 0 ? <p className="section-label">Postponed: {data.backlog}</p> : null}
    </div>
  );
}
