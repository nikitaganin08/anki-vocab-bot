import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useLayoutEffect, useState } from "react";

import { EmptyState } from "./components/PageState";
import { TabBar } from "./components/TabBar";
import { HomeView, type ReviewMode } from "./home/HomeView";
import { useView, type View } from "./navigation";
import { CardsPage } from "./pages/CardsPage";
import { ReviewView } from "./review/ReviewView";
import {
  applyTelegramTheme,
  hasTelegramWebAppContext,
  prepareTelegramWebApp,
  showBackButton,
} from "./telegram";

// Placeholder until SettingsView lands.
function renderView(
  view: View,
  mode: ReviewMode,
  openView: (v: View, mode?: ReviewMode) => void,
): JSX.Element {
  switch (view) {
    case "home":
      return <HomeView onStart={(startMode) => openView("review", startMode)} />;
    case "review":
      return <ReviewView mode={mode} onExit={() => openView("home")} />;
    case "cards":
      return <CardsPage />;
    case "settings":
      return <EmptyState title="Настройки" message="Здесь будут настройки повторения." />;
  }
}

export function App(): JSX.Element {
  const telegramContextAvailable = hasTelegramWebAppContext();
  const [view, setView] = useView();
  // Start options from Главная; the tab, the reminder and /review open a plain session.
  const [mode, setMode] = useState<ReviewMode>({});
  const openView = (next: View, nextMode: ReviewMode = {}): void => {
    setMode(nextMode);
    setView(next);
  };
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            retry: 1,
            refetchOnWindowFocus: false,
          },
        },
      }),
  );

  // Layout effect: theme variables land before the first paint, no light flash in dark Telegram.
  useLayoutEffect(() => {
    prepareTelegramWebApp();
    applyTelegramTheme();
  }, []);

  useEffect(() => (view === "review" ? showBackButton(() => setView("home")) : undefined), [view]);

  if (!telegramContextAvailable) {
    return (
      <main className="telegram-gate-shell">
        <EmptyState
          title="Open This Panel From Telegram"
          message="Use the /admin command in your bot chat to launch the dictionary panel inside Telegram."
        />
      </main>
    );
  }

  return (
    <QueryClientProvider client={queryClient}>
      <div className="app-shell">
        <main className="page-shell">{renderView(view, mode, openView)}</main>
        <TabBar view={view} onChange={openView} />
      </div>
    </QueryClientProvider>
  );
}
