import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { getSpeakingIssues, getSpeakingSession, getSpeakingStats } from "../api/client";
import type { SpeakingCategory, SpeakingIssue } from "../api/types";
import { EmptyState, ErrorState, LoadingState } from "../components/PageState";
import { Sheet } from "../components/Sheet";

function shortDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en", { month: "short", day: "numeric" });
}

function duration(seconds: number): string {
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

function Fix({ issue }: { issue: SpeakingIssue }): JSX.Element {
  return (
    <span className="speaking-fix">
      {issue.wrong !== null && issue.right !== null ? (
        <span>
          <s>{issue.wrong}</s> → <strong>{issue.right}</strong>
        </span>
      ) : null}
      <em className="section-label">{issue.why}</em>
    </span>
  );
}

function CategorySheet({
  category,
  onClose,
  onOpenRecording,
}: {
  category: SpeakingCategory;
  onClose: () => void;
  onOpenRecording: (sessionId: number) => void;
}): JSX.Element {
  const issues = useQuery({
    queryKey: ["speaking-issues", category.category],
    queryFn: () => getSpeakingIssues(category.category),
  });
  return (
    <Sheet label={category.label} onClose={onClose}>
      <h2 className="sheet-title">
        {category.label} · {category.count}
      </h2>
      {issues.error ? <ErrorState error={issues.error} onRetry={() => void issues.refetch()} /> : null}
      {issues.data ? (
        <ul className="word-list">
          {issues.data.map((issue) => (
            <li key={issue.id}>
              <button type="button" className="word-row issue-row" onClick={() => onOpenRecording(issue.session_id)}>
                <Fix issue={issue} />
                <span className="word-row-label">{shortDate(issue.recorded_at)}</span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
      <div className="sheet-actions-single">
        <button type="button" className="secondary-button" onClick={onClose}>
          Close
        </button>
      </div>
    </Sheet>
  );
}

function RecordingSheet({ sessionId, onClose }: { sessionId: number; onClose: () => void }): JSX.Element {
  const detail = useQuery({
    queryKey: ["speaking-session", sessionId],
    queryFn: () => getSpeakingSession(sessionId),
  });
  const data = detail.data;
  return (
    <Sheet label="Recording" onClose={onClose}>
      {detail.error ? <ErrorState error={detail.error} onRetry={() => void detail.refetch()} /> : null}
      {data ? (
        <>
          <h2 className="sheet-title">{data.topic ?? "Free speech"}</h2>
          <p className="section-label">
            {shortDate(data.recorded_at)} · {duration(data.duration_seconds)} ·{" "}
            {data.kind === "voice" ? "voice" : "video note"} · fillers {data.filler_count}
            {data.focus_check ? ` · last focus: ${data.focus_check}` : ""}
          </p>
          {data.words.length > 0 ? (
            <p>
              {data.words.map((w) => (
                <span key={w.word} className="speaking-word">
                  {w.used ? "✅" : "❌"} {w.word}
                </span>
              ))}
            </p>
          ) : null}
          {data.issues.length > 0 ? (
            <section>
              <span className="section-label">Fixes</span>
              <ol className="speaking-fixes">
                {data.issues.map((issue) => (
                  <li key={issue.id}>
                    <Fix issue={issue} />
                  </li>
                ))}
              </ol>
            </section>
          ) : null}
          {data.natural_version ? (
            <section>
              <span className="section-label">Say it like this</span>
              <blockquote className="speaking-quote">{data.natural_version}</blockquote>
            </section>
          ) : null}
          <p>
            <strong>Next time:</strong> {data.next_time}
          </p>
          <details>
            <summary>What you said</summary>
            <p className="speaking-transcript">{data.transcript}</p>
          </details>
        </>
      ) : null}
      <div className="sheet-actions-single">
        <button type="button" className="secondary-button" onClick={onClose}>
          Close
        </button>
      </div>
    </Sheet>
  );
}

export function SpeakingView(): JSX.Element {
  const { data, error, refetch } = useQuery({ queryKey: ["speaking-stats"], queryFn: getSpeakingStats });
  const [category, setCategory] = useState<SpeakingCategory | null>(null);
  const [sessionId, setSessionId] = useState<number | null>(null);

  if (error) {
    return <ErrorState error={error} onRetry={() => void refetch()} />;
  }
  if (!data) {
    return <LoadingState title="Speaking" message="Loading your recordings…" />;
  }
  if (data.sessions.length === 0) {
    return (
      <EmptyState
        title="No recordings yet"
        message="Answer the daily topic in the bot with a voice message or a video note."
      />
    );
  }

  const top = data.categories[0]?.count ?? 1;
  const fillers =
    data.filler_rate === null
      ? "—"
      : data.filler_rate_prev === null
        ? String(data.filler_rate)
        : `${data.filler_rate_prev} → ${data.filler_rate}`;

  return (
    <div className="speaking-view">
      <h2>Speaking</h2>
      <div className="stat-grid">
        <section className="surface-panel stat-tile">
          <span className="section-label">Recordings, 30 days</span>
          <strong>{data.recordings}</strong>
        </section>
        <section className="surface-panel stat-tile">
          <span className="section-label">Minutes</span>
          <strong>{data.minutes}</strong>
        </section>
        <section className="surface-panel stat-tile">
          <span className="section-label">Fillers per minute</span>
          <strong>{fillers}</strong>
        </section>
        <section className="surface-panel stat-tile">
          <span className="section-label">Deck words used</span>
          <strong>
            {data.words_used} of {data.words_total}
          </strong>
        </section>
      </div>

      {data.categories.length > 0 ? (
        <section className="surface-panel">
          <span className="section-label">Your patterns · 30 days</span>
          <ul className="pattern-list">
            {data.categories.map((item) => (
              <li key={item.category}>
                <button type="button" className="pattern-row" onClick={() => setCategory(item)}>
                  <span>{item.label}</span>
                  <span className="section-label">{item.count}</span>
                  <span className="pattern-bar" style={{ width: `${(item.count / top) * 100}%` }} />
                </button>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <span className="section-label">Recordings</span>
      <ul className="word-list">
        {data.sessions.map((row) => (
          <li key={row.id}>
            <button type="button" className="word-row" onClick={() => setSessionId(row.id)}>
              <span aria-hidden="true">{row.kind === "voice" ? "🎙" : "📹"}</span>
              <span className="word-row-text">
                <strong>
                  {shortDate(row.recorded_at)} · {duration(row.duration_seconds)}
                </strong>
                <span className="word-row-translation">{row.topic ?? "Free speech"}</span>
              </span>
              <span className="word-row-label">
                {row.fix_count} {row.fix_count === 1 ? "fix" : "fixes"}
              </span>
            </button>
          </li>
        ))}
      </ul>

      {category ? (
        <CategorySheet
          category={category}
          onClose={() => setCategory(null)}
          onOpenRecording={(id) => {
            setCategory(null);
            setSessionId(id);
          }}
        />
      ) : null}
      {sessionId !== null ? <RecordingSheet sessionId={sessionId} onClose={() => setSessionId(null)} /> : null}
    </div>
  );
}
