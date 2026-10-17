// A day counts toward the streak at 5+ typed answers (backend STREAK_MIN_ANSWERS).
const FULL_DAY_ANSWERS = 5;

// One hue in two strengths; missed days stay neutral grey, never red.
function level(count: number): number {
  return count === 0 ? 0 : count < FULL_DAY_ANSWERS ? 1 : 2;
}

// counts: 98 study days, oldest first; columns are weeks, today is the last cell.
export function Heatmap({ counts }: { counts: number[] }): JSX.Element {
  return (
    <div className="heatmap" role="img" aria-label="Активность за 14 недель">
      {counts.map((count, i) => (
        <span key={i} className="heatmap-cell" data-level={level(count)} />
      ))}
    </div>
  );
}
