interface LoadingStateProps {
  title?: string;
  message?: string;
}

interface EmptyStateProps {
  title: string;
  message: string;
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

  return "Неизвестная ошибка";
}

export function LoadingState({ title = "Загрузка", message = "Загружаем данные…" }: LoadingStateProps): JSX.Element {
  return (
    <section className="page-state" role="status" aria-live="polite">
      <div className="pulse-dot" aria-hidden="true" />
      <h2>{title}</h2>
      <p>{message}</p>
    </section>
  );
}

export function EmptyState({ title, message }: EmptyStateProps): JSX.Element {
  return (
    <section className="page-state">
      <h2>{title}</h2>
      <p>{message}</p>
    </section>
  );
}

export function ErrorState({ title = "Не удалось загрузить", error, onRetry }: ErrorStateProps): JSX.Element {
  return (
    <section className="page-state page-state-error" role="alert">
      <h2>{title}</h2>
      <p>{getErrorMessage(error)}</p>
      {onRetry ? (
        <button type="button" className="secondary-button" onClick={onRetry}>
          Повторить
        </button>
      ) : null}
    </section>
  );
}
