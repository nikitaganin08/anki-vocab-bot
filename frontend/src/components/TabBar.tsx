import type { View } from "../navigation";

interface TabBarProps {
  view: View;
  onChange: (view: View) => void;
}

// Tabler outline icon paths (MIT), 24x24.
const TABS: { view: View; label: string; paths: string[] }[] = [
  {
    view: "home",
    label: "Главная",
    paths: ["M5 12H3l9-9 9 9h-2", "M5 12v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-7", "M9 21v-6a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v6"],
  },
  {
    view: "review",
    label: "Повтор",
    paths: ["M4 12V9a3 3 0 0 1 3-3h13m-3-3 3 3-3 3", "M20 12v3a3 3 0 0 1-3 3H4m3 3-3-3 3-3"],
  },
  {
    view: "cards",
    label: "Слова",
    paths: ["M3 19a9 9 0 0 1 9 0 9 9 0 0 1 9 0", "M3 6a9 9 0 0 1 9 0 9 9 0 0 1 9 0", "M3 6v13M12 6v13M21 6v13"],
  },
  {
    view: "settings",
    label: "Настройки",
    paths: ["M4 6h8m4 0h4M4 12h2m4 0h10M4 18h11m4 0h1", "M12 6a2 2 0 1 0 4 0 2 2 0 1 0-4 0", "M6 12a2 2 0 1 0 4 0 2 2 0 1 0-4 0", "M15 18a2 2 0 1 0 4 0 2 2 0 1 0-4 0"],
  },
];

export function TabBar({ view, onChange }: TabBarProps): JSX.Element | null {
  if (view === "review") {
    return null;
  }

  return (
    <nav className="tab-bar" aria-label="Разделы">
      {TABS.map((tab) => (
        <button
          key={tab.view}
          type="button"
          className="tab-bar-item"
          aria-current={tab.view === view ? "page" : undefined}
          onClick={() => onChange(tab.view)}
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            {tab.paths.map((d) => (
              <path key={d} d={d} />
            ))}
          </svg>
          <span>{tab.label}</span>
        </button>
      ))}
    </nav>
  );
}
