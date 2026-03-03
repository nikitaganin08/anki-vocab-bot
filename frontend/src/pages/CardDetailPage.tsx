import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { getCard } from "../api/client";
import { EmptyState, ErrorState, LoadingState } from "../components/PageState";

function formatDate(value: string): string {
  const date = new Date(value);
  return date.toLocaleString();
}

function formatEntryType(value: string): string {
  return value.replaceAll("_", " ");
}

export function CardDetailPage(): JSX.Element {
  const { cardId } = useParams();
  const parsedId = Number(cardId);

  if (!Number.isInteger(parsedId) || parsedId <= 0) {
    return (
      <ErrorState
        title="Invalid card ID"
        error={new Error("The requested card ID is not valid.")}
      />
    );
  }

  const cardQuery = useQuery({
    queryKey: ["card", parsedId],
    queryFn: () => getCard(parsedId),
  });

  if (cardQuery.isLoading) {
    return <LoadingState title="Loading card" message="Fetching card details." />;
  }

  if (cardQuery.isError) {
    return <ErrorState error={cardQuery.error} onRetry={() => void cardQuery.refetch()} />;
  }

  const card = cardQuery.data;
  if (!card) {
    return <EmptyState title="Card not found" message="The API returned no data for this card." />;
  }

  return (
    <article className="detail-page">
      <header className="detail-header">
        <div>
          <p className="eyebrow">Card #{card.id}</p>
          <h2>{card.canonical_text}</h2>
          {card.transcription ? <p className="transcription">{card.transcription}</p> : null}
        </div>
        <Link to="/cards" className="secondary-button back-link">
          Back to cards
        </Link>
      </header>

      <section className="panel">
        <h3>Translations</h3>
        <ul className="translation-list">
          {card.translation_variants.map((variant) => (
            <li key={variant}>{variant}</li>
          ))}
        </ul>
      </section>

      <section className="panel">
        <h3>Explanation</h3>
        <p>{card.explanation}</p>
      </section>

      <section className="panel">
        <h3>Examples</h3>
        <ol className="example-list">
          {card.examples.map((example) => (
            <li key={example}>{example}</li>
          ))}
        </ol>
      </section>

      <section className="panel">
        <h3>Metadata</h3>
        <dl className="meta-grid">
          <div>
            <dt>Source text</dt>
            <dd>{card.source_text}</dd>
          </div>
          <div>
            <dt>Source language</dt>
            <dd>{card.source_language.toUpperCase()}</dd>
          </div>
          <div>
            <dt>Entry type</dt>
            <dd>{formatEntryType(card.entry_type)}</dd>
          </div>
          <div>
            <dt>Frequency</dt>
            <dd>{card.frequency}</dd>
          </div>
          <div>
            <dt>Anki status</dt>
            <dd>{card.anki_sync_status}</dd>
          </div>
          <div>
            <dt>Eligible for Anki</dt>
            <dd>{card.eligible_for_anki ? "yes" : "no"}</dd>
          </div>
          <div>
            <dt>Created at</dt>
            <dd>{formatDate(card.created_at)}</dd>
          </div>
          <div>
            <dt>Updated at</dt>
            <dd>{formatDate(card.updated_at)}</dd>
          </div>
          <div>
            <dt>LLM model</dt>
            <dd>{card.llm_model}</dd>
          </div>
        </dl>
      </section>
    </article>
  );
}
