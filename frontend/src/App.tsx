import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useLayoutEffect, useState } from "react";

import { EmptyState } from "./components/PageState";
import { TabBar } from "./components/TabBar";
import { HomeView } from "./home/HomeView";
import { useView, type View } from "./navigation";
import { CardsPage } from "./pages/CardsPage";
import {
  applyTelegramTheme,
  hasTelegramWebAppContext,
  prepareTelegramWebApp,
  showBackButton,
} from "./telegram";

// Placeholders until ReviewView and SettingsView land; the start mode reaches ReviewView in Task 4.
function renderView(view: View, setView: (v: View) => void): JSX.Element {
  switch (view) {
    case "home":
      return <HomeView onStart={() => setView("review")} />;
    case "review":
      return <EmptyState title="Повтор" message="Здесь будет повторение карточек." />;
    case "cards":
      return <CardsPage />;
    case "settings":
      return <EmptyState title="Настройки" message="Здесь будут настройки повторения." />;
  }
}

export function App(): JSX.Element {
  const telegramContextAvailable = hasTelegramWebAppContext();
  const [view, setView] = useView();
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
        <main className="page-shell">{renderView(view, setView)}</main>
        <TabBar view={view} onChange={setView} />
      </div>
    </QueryClientProvider>
  );
}
