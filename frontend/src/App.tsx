import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { EmptyState } from "./components/PageState";
import { CardsPage } from "./pages/CardsPage";
import { hasTelegramWebAppContext, prepareTelegramWebApp } from "./telegram";

export function App(): JSX.Element {
  const telegramContextAvailable = hasTelegramWebAppContext();
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

  useEffect(() => {
    prepareTelegramWebApp();
  }, []);

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
      <div className="admin-shell">
        <header className="app-header">
          <div className="brand-block">
            <p className="eyebrow">anki-vocab-bot</p>
            <h1>Telegram Dictionary Panel</h1>
          </div>

          <p className="eyebrow">Manage cards inside Telegram</p>
        </header>

        <main className="page-shell">
          <CardsPage />
        </main>
      </div>
    </QueryClientProvider>
  );
}
