import { useQuery } from "@tanstack/react-query";

import { getStats } from "../api/client";
import { EmptyState, ErrorState, LoadingState } from "../components/PageState";

interface MetricCardProps {
  label: string;
  value: number;
  tone?: "neutral" | "positive" | "warning";
}

function MetricCard({ label, value, tone = "neutral" }: MetricCardProps): JSX.Element {
  return (
    <article className={`metric-card metric-${tone}`}>
      <p>{label}</p>
      <strong>{value.toLocaleString()}</strong>
    </article>
  );
}

export function DashboardPage(): JSX.Element {
  const statsQuery = useQuery({
    queryKey: ["stats"],
    queryFn: getStats,
  });

  if (statsQuery.isLoading) {
    return <LoadingState title="Loading dashboard" message="Collecting card and queue statistics." />;
  }

  if (statsQuery.isError) {
    return <ErrorState error={statsQuery.error} onRetry={() => void statsQuery.refetch()} />;
  }

  const stats = statsQuery.data;
  if (!stats) {
    return (
      <EmptyState
        title="No dashboard data"
        message="The API returned an empty response for statistics."
      />
    );
  }

  return (
    <section className="dashboard-grid">
      <header className="page-title-block">
        <h2>Dashboard</h2>
        <p>Operational view of cards and the Anki sync queue.</p>
      </header>

      <div className="metric-grid">
        <MetricCard label="Total cards" value={stats.total_cards} />
        <MetricCard label="Eligible for Anki" value={stats.eligible_for_anki} tone="positive" />
        <MetricCard label="Sync pending" value={stats.anki_pending} tone="warning" />
        <MetricCard label="Synced" value={stats.anki_synced} tone="positive" />
        <MetricCard label="Failed" value={stats.anki_failed} tone="warning" />
      </div>

      <div className="panel-grid">
        <section className="panel">
          <h3>Cards by entry type</h3>
          <ul className="count-list">
            {Object.entries(stats.by_entry_type).map(([entryType, count]) => (
              <li key={entryType}>
                <span>{entryType.replaceAll("_", " ")}</span>
                <strong>{count}</strong>
              </li>
            ))}
          </ul>
        </section>

        <section className="panel">
          <h3>Cards by source language</h3>
          <ul className="count-list">
            {Object.entries(stats.by_source_language).map(([language, count]) => (
              <li key={language}>
                <span>{language.toUpperCase()}</span>
                <strong>{count}</strong>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </section>
  );
}
