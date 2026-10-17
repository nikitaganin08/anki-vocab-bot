// A day counts toward the streak at 5+ typed answers (backend STREAK_MIN_ANSWERS).
const FULL_DAY_ANSWERS = 5;

// One hue in two strengths; missed days stay neutral grey, never red.
function level(count: number): number {
  return count === 0 ? 0 : count < FULL_DAY_ANSWERS ? 1 : 2;
}

// Study days start at 06:00 (backend DAY_START_HOUR).
const DAY_START_MS = 6 * 3_600_000;

// counts: 98 study days, oldest first; columns are weeks, rows Monday→Sunday, today is the last cell.
// ponytail: weekday from the browser clock; assumes the browser timezone matches the settings one.
export function Heatmap({ counts }: { counts: number[] }): JSX.Element {
  const todayRow = (new Date(Date.now() - DAY_START_MS).getDay() + 6) % 7; // Monday = 0
  // The first cell starts at its weekday's row; the rest flow down the columns after it.
  const firstRow = (((todayRow - (counts.length - 1)) % 7) + 7) % 7;
  return (
    <div className="heatmap" role="img" aria-label="Активность за 14 недель">
      {counts.map((count, i) => (
        <span
          key={i}
          className="heatmap-cell"
          data-level={level(count)}
          style={i === 0 ? { gridRowStart: firstRow + 1 } : undefined}
        />
      ))}
    </div>
  );
}
