import { Sheet } from "../components/Sheet";
import { ENTRY_TYPES } from "../entryTypes";

export function EntryTypesSheet({ onClose }: { onClose: () => void }): JSX.Element {
  return (
    <Sheet label="Card types" onClose={onClose}>
      <h3 className="sheet-title">Card types</h3>
      <dl className="type-legend">
        {ENTRY_TYPES.map((type) => (
          <div key={type.value}>
            <dt>{type.label}</dt>
            <dd>
              {type.description}
              <span className="section-label"> · {type.example}</span>
            </dd>
          </div>
        ))}
      </dl>
      <button type="button" className="secondary-button" onClick={onClose}>
        Close
      </button>
    </Sheet>
  );
}
