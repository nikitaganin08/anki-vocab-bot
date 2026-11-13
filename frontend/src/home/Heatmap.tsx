interface HeatmapProps {
  goalMet: boolean[];
  speaking: boolean[];
}

// 98 study days, oldest first; columns are weeks, rows Monday→Sunday, today is the last cell.
// Each cell is split in two: left half filled when the review goal was closed that day, right half
// when a speaking recording was analysed. Missed halves stay neutral grey, never red.
// Study days start at local midnight (backend DAY_START_HOUR = 0), so today is the calendar day.
// ponytail: weekday from the browser clock; matches the settings timezone, which follows the device.
export function Heatmap({ goalMet, speaking }: HeatmapProps): JSX.Element {
  const todayRow = (new Date().getDay() + 6) % 7; // Monday = 0
  // The first cell starts at its weekday's row; the rest flow down the columns after it.
  const firstRow = (((todayRow - (goalMet.length - 1)) % 7) + 7) % 7;
  return (
    <>
      <div className="heatmap" role="img" aria-label="Activity over 14 weeks">
        {goalMet.map((met, i) => (
          <span
            key={i}
            className="heatmap-cell"
            data-review={met ? "done" : undefined}
            data-speaking={speaking[i] ? "done" : undefined}
            style={i === 0 ? { gridRowStart: firstRow + 1 } : undefined}
          />
        ))}
      </div>
      <p className="heatmap-legend section-label">
        <span className="heatmap-key heatmap-key-review" aria-hidden="true" /> review done
        <span className="heatmap-key heatmap-key-speaking" aria-hidden="true" /> speaking
      </p>
    </>
  );
}
