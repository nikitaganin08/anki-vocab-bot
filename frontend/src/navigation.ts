import { useState } from "react";

export type View = "home" | "review" | "cards" | "settings";

const VIEWS: readonly string[] = ["home", "review", "cards", "settings"];

export function readView(search: string): View {
  const view = new URLSearchParams(search).get("view") ?? "";
  return VIEWS.includes(view) ? (view as View) : "home";
}

// replaceState (not pushState) keeps tab switches out of Telegram's back navigation.
export function useView(): [View, (v: View) => void] {
  const [view, setViewState] = useState(() => readView(window.location.search));
  const setView = (next: View): void => {
    const params = new URLSearchParams(window.location.search);
    params.set("view", next);
    window.history.replaceState(null, "", `${window.location.pathname}?${params}`);
    setViewState(next);
  };
  return [view, setView];
}
