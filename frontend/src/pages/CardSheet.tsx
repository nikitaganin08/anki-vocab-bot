import { useMutation } from "@tanstack/react-query";
import { useRef, useState } from "react";

import { deleteCard, setCardLearning } from "../api/client";
import type { Card } from "../api/types";
import { ErrorState } from "../components/PageState";
import { Sheet, trapTab } from "../components/Sheet";
import { CardDetails } from "../review/IntroCard";

interface CardSheetProps {
  card: Card;
  onClose: () => void;
  onLearningSaved: (card: Card) => void;
  onDeleted: () => void;
}

export function CardSheet({ card, onClose, onLearningSaved, onDeleted }: CardSheetProps): JSX.Element {
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const deleteButtonRef = useRef<HTMLButtonElement>(null);

  const learningMutation = useMutation({
    mutationFn: (isLearning: boolean) => setCardLearning(card.id, isLearning),
    onSuccess: onLearningSaved,
  });
  const deleteMutation = useMutation({
    mutationFn: () => deleteCard(card.id),
    onSuccess: onDeleted,
  });

  const cancelDelete = (): void => {
    deleteMutation.reset();
    setConfirmingDelete(false);
    deleteButtonRef.current?.focus();
  };

  return (
    <>
      {/* Escape closes the confirm dialog first, the sheet only when none is open. */}
      <Sheet label={card.canonical_text} onClose={confirmingDelete ? cancelDelete : onClose}>
        <CardDetails card={card} />

        <label className="learning-toggle">
          <input
            type="checkbox"
            role="switch"
            checked={card.is_learning}
            disabled={learningMutation.isPending}
            onChange={(event) => learningMutation.mutate(event.target.checked)}
          />
          Learning
        </label>

        {learningMutation.isError ? (
          <ErrorState title="Couldn't save “Learning”" error={learningMutation.error} />
        ) : null}

        <div className="sheet-actions">
          <button
            ref={deleteButtonRef}
            type="button"
            className="danger-button"
            onClick={() => setConfirmingDelete(true)}
          >
            Delete
          </button>
          <button type="button" className="secondary-button" onClick={onClose}>
            Close
          </button>
        </div>
      </Sheet>

      {confirmingDelete ? (
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
                onClick={cancelDelete}
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
      ) : null}
    </>
  );
}
