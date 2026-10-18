import { useMutation } from "@tanstack/react-query";

import { deleteCard } from "../api/client";
import type { Card } from "../api/types";
import { trapTab } from "./Sheet";

interface DeleteCardDialogProps {
  card: Card;
  onCancel: () => void;
  onDeleted: () => void;
}

export function DeleteCardDialog({ card, onCancel, onDeleted }: DeleteCardDialogProps): JSX.Element {
  const deleteMutation = useMutation({
    mutationFn: () => deleteCard(card.id),
    onSuccess: onDeleted,
  });

  return (
    <div className="modal-backdrop" role="presentation">
      <section
        className="confirm-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="delete-card-title"
        tabIndex={-1}
        onKeyDown={trapTab}
      >
        <p className="section-label">Delete</p>
        <h3 id="delete-card-title" className="sheet-title">Delete “{card.canonical_text}”?</h3>
        <p>The card will be removed from your dictionary.</p>

        {deleteMutation.isError ? (
          <p className="batch-message batch-message-error">{deleteMutation.error.message}</p>
        ) : null}

        <div className="confirm-dialog-actions">
          <button
            type="button"
            className="secondary-button"
            autoFocus
            disabled={deleteMutation.isPending}
            onClick={() => {
              deleteMutation.reset();
              onCancel();
            }}
          >
            Cancel
          </button>
          <button
            type="button"
            className="danger-button"
            disabled={deleteMutation.isPending}
            onClick={() => deleteMutation.mutate()}
          >
            {deleteMutation.isPending ? "Deleting…" : "Delete card"}
          </button>
        </div>
      </section>
    </div>
  );
}
