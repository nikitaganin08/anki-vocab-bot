import type { CheckResponse } from "../api/types";

const GRADES = [
  { rating: 1, label: "Again" },
  { rating: 2, label: "Hard" },
  { rating: 3, label: "Good" },
  { rating: 4, label: "Easy" },
];

// Round first, then pick the unit: 3570 s is "1h", not "60m".
export function formatInterval(seconds: number): string {
  if (seconds < 60) {
    return "<1m";
  }
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) {
    return `${minutes}m`;
  }
  const hours = Math.round(seconds / 3600);
  if (hours < 24) {
    return `${hours}h`;
  }
  return `${Math.round(seconds / 86400)}d`;
}

interface GradeGridProps {
  result: CheckResponse;
  busy: boolean;
  autoFocus?: boolean;
  onGrade: (rating: number) => void;
}

// The four grade buttons with their next intervals; the auto rating is highlighted.
export function GradeGrid({ result, busy, autoFocus = false, onGrade }: GradeGridProps): JSX.Element {
  return (
    <div className="grade-grid">
      {GRADES.map(({ rating, label }) => (
        <button
          key={rating}
          type="button"
          className={rating === result.auto_rating ? "primary-button" : "secondary-button"}
          autoFocus={autoFocus && rating === result.auto_rating}
          disabled={busy}
          onClick={() => onGrade(rating)}
        >
          <span>{label}</span>
          <span className="grade-interval">{formatInterval(result.intervals[rating])}</span>
        </button>
      ))}
    </div>
  );
}
