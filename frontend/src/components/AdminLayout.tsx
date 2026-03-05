import { Outlet } from "react-router-dom";

export function AdminLayout(): JSX.Element {
  return (
    <div className="admin-shell">
      <header className="app-header">
        <div className="brand-block">
          <p className="eyebrow">anki-vocab-bot</p>
          <h1>Admin Console</h1>
        </div>

        <p className="eyebrow">Cards list and deletion</p>
      </header>

      <main className="page-shell">
        <Outlet />
      </main>
    </div>
  );
}
