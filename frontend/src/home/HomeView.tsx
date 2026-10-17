import { useQuery } from "@tanstack/react-query";

import { getReviewSummary } from "../api/client";
import type { ReviewSummary } from "../api/types";
import { ErrorState, LoadingState } from "../components/PageState";
import { Heatmap } from "./Heatmap";

export interface ReviewMode {
  includeBacklog?: boolean;
  // The session ends after this many graded cards ("Быстро", "5 минут").
  capCards?: number;
}

interface HomeViewProps {
  onStart: (mode: ReviewMode) => void;
}

const CARD_FORMS: Record<string, string> = {
  one: "карточка",
  few: "карточки",
  many: "карточек",
  other: "карточки",
};

export function cardsLabel(count: number): string {
  return `${count} ${CARD_FORMS[new Intl.PluralRules("ru").select(count)]}`;
}

// "5 минут": as many cards as fit in 5 minutes at today's pace, at least 5.
function fiveMinuteCap(summary: ReviewSummary): number {
  const perCard = summary.est_minutes / Math.max(summary.due_today + summary.new_today, 1);
  return perCard > 0 ? Math.max(5, Math.ceil(5 / perCard)) : 5;
}

function GoalCard({ summary, onStart }: { summary: ReviewSummary } & HomeViewProps): JSX.Element {
  const goal = summary.due_today + summary.new_today;
  return (
    <section className="surface-panel home-card">
      <h2>
        Цель на сегодня: {cardsLabel(goal)} · ~{summary.est_minutes} мин
      </h2>
      <button type="button" className="primary-button" onClick={() => onStart({})}>
        Начать
      </button>
      <button type="button" className="secondary-button" onClick={() => onStart({ capCards: 5 })}>
        Быстро: 5 карточек
      </button>
    </section>
  );
}

function WelcomeBack({ summary, onStart }: { summary: ReviewSummary } & HomeViewProps): JSX.Element {
  return (
    <section className="surface-panel home-card">
      <h2>С возвращением</h2>
      <p className="section-label">Как сегодня?</p>
      <button
        type="button"
        className="primary-button"
        onClick={() => onStart({ capCards: fiveMinuteCap(summary) })}
      >
        5 минут
      </button>
      <button type="button" className="secondary-button" onClick={() => onStart({})}>
        Обычная сессия
      </button>
      <button
        type="button"
        className="secondary-button"
        onClick={() => onStart({ includeBacklog: true })}
      >
        Всё сразу ({summary.due_all})
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
    return <LoadingState title="Главная" message="Загружаем цель на сегодня…" />;
  }

  const welcomeBack = data.days_away !== null && data.days_away >= 3 && data.due_all > 0;
  const retention =
    data.retention_30d === null ? "—" : `${Math.round(data.retention_30d * 100)}%`;

  return (
    <div className="home-view">
      {welcomeBack ? (
        <WelcomeBack summary={data} onStart={onStart} />
      ) : (
        <GoalCard summary={data} onStart={onStart} />
      )}

      <div className="stat-grid">
        <section className="surface-panel stat-tile">
          <span className="section-label">Удержание за 30 дн.</span>
          <strong>{retention}</strong>
          <span className="section-label">цель 90%</span>
        </section>
        <section className="surface-panel stat-tile">
          <span className="section-label">Выучено</span>
          <strong>{data.learned_total}</strong>
          <span className="section-label">+{data.learned_delta_7d} за неделю</span>
        </section>
      </div>

      <section className="surface-panel home-activity">
        <span className="section-label">Активность</span>
        <Heatmap counts={data.heatmap} />
        {data.streak_days >= 3 ? (
          <p className="section-label">
            серия {data.streak_days} дн. · лучшая {data.best_streak_days}
          </p>
        ) : null}
      </section>

      <p className="section-label">
        Завтра ~{data.forecast_tomorrow} · неделя ~{data.forecast_week_avg}/день
      </p>
      {data.backlog > 0 ? <p className="section-label">Отложено: {data.backlog}</p> : null}
    </div>
  );
}
