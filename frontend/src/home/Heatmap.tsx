import type { CSSProperties } from "react";

interface HeatmapProps {
  goalMet: boolean[];
  speaking: boolean[];
}

const WEEKDAYS = ["M", "T", "W", "T", "F", "S", "S"];

// The current month as a calendar (rows are weeks, Monday first). Each past day is split in two:
// left half when the review goal was closed, right half when a speaking recording was analysed.
// goalMet / speaking: the last 98 study days, oldest first, today last. Study days start at local
// midnight (backend DAY_START_HOUR = 0), so today is the calendar day.
// ponytail: dates from the browser clock; matches the settings timezone, which follows the device.
export function Heatmap({ goalMet, speaking }: HeatmapProps): JSX.Element {
  const now = new Date();
  const today = now.getDate();
  const daysInMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
  const firstWeekday = (new Date(now.getFullYear(), now.getMonth(), 1).getDay() + 6) % 7;
  const last = goalMet.length - 1;
  const at = (list: boolean[], day: number): boolean => list[last - (today - day)] ?? false;
  const days = Array.from({ length: daysInMonth }, (_, i) => i + 1);
  const closed = days.filter((day) => day <= today && at(goalMet, day)).length;
  const spoken = days.filter((day) => day <= today && at(speaking, day)).length;
  const month = now.toLocaleDateString("en", { month: "long", year: "numeric" });
  const weeks = Math.ceil((firstWeekday + daysInMonth) / 7);

  return (
    <>
      <span className="section-label">Activity · {month}</span>
      <div
        className="month-calendar"
        role="img"
        aria-label={`Activity in ${month}`}
        style={{ "--weeks": weeks } as CSSProperties}
      >
        {WEEKDAYS.map((name, i) => (
          <span key={`wd-${i}`} className="month-weekday" aria-hidden="true">
            {name}
          </span>
        ))}
        {days.map((day) => (
          <span
            key={day}
            className="month-day"
            data-review={day <= today && at(goalMet, day) ? "done" : undefined}
            data-speaking={day <= today && at(speaking, day) ? "done" : undefined}
            data-today={day === today ? "true" : undefined}
            data-future={day > today ? "true" : undefined}
            style={day === 1 ? { gridColumnStart: firstWeekday + 1 } : undefined}
          >
            {day}
          </span>
        ))}
      </div>
      <p className="heatmap-legend section-label">
        <span className="heatmap-key heatmap-key-review" aria-hidden="true" /> review {closed}
        <span className="heatmap-key heatmap-key-speaking" aria-hidden="true" /> speaking {spoken} of{" "}
        {today} days
      </p>
    </>
  );
}
