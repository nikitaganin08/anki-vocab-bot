import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AdminLayout } from "./components/AdminLayout";
import { EmptyState } from "./components/PageState";
import { CardsPage } from "./pages/CardsPage";
import { resolveWebAppBasename } from "./routing";
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
      <BrowserRouter basename={resolveWebAppBasename()}>
        <Routes>
          <Route path="/" element={<AdminLayout />}>
            <Route index element={<CardsPage />} />
            <Route path="cards" element={<CardsPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
