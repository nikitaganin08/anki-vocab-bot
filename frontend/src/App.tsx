import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AdminLayout } from "./components/AdminLayout";
import { CardsPage } from "./pages/CardsPage";

function resolveBasename(): string | undefined {
  if (
    import.meta.env.BASE_URL === "/admin/" &&
    window.location.pathname.startsWith("/admin")
  ) {
    return "/admin";
  }

  return undefined;
}

export function App(): JSX.Element {
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

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter basename={resolveBasename()}>
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
