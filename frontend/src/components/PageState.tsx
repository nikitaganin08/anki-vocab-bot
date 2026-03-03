import type { ReactNode } from "react";

interface LoadingStateProps {
  title?: string;
  message?: string;
}

interface EmptyStateProps {
  title: string;
  message: string;
  action?: ReactNode;
}

interface ErrorStateProps {
  title?: string;
  error: unknown;
  onRetry?: () => void;
}

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }

  return "Unexpected error";
}

export function LoadingState({
  title = "Loading",
  message = "Fetching the latest data.",
}: LoadingStateProps): JSX.Element {
  return (
    <section className="page-state" role="status" aria-live="polite">
      <div className="pulse-dot" aria-hidden="true" />
      <h2>{title}</h2>
      <p>{message}</p>
    </section>
  );
}

export function EmptyState({ title, message, action }: EmptyStateProps): JSX.Element {
  return (
    <section className="page-state">
      <h2>{title}</h2>
      <p>{message}</p>
      {action ? <div className="state-action">{action}</div> : null}
    </section>
  );
}

export function ErrorState({ title = "Could not load data", error, onRetry }: ErrorStateProps): JSX.Element {
  return (
    <section className="page-state page-state-error" role="alert">
      <h2>{title}</h2>
      <p>{getErrorMessage(error)}</p>
      {onRetry ? (
        <button type="button" className="secondary-button" onClick={onRetry}>
          Try again
        </button>
      ) : null}
    </section>
  );
}
