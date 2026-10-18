import { useMutation } from "@tanstack/react-query";
import { useRef, useState } from "react";

import { setCardLearning } from "../api/client";
import type { Card } from "../api/types";
import { ErrorState } from "../components/PageState";
import { DeleteCardDialog } from "../components/DeleteCardDialog";
import { Sheet } from "../components/Sheet";
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

  const cancelDelete = (): void => {
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
        <DeleteCardDialog card={card} onCancel={cancelDelete} onDeleted={onDeleted} />
      ) : null}
    </>
  );
}
