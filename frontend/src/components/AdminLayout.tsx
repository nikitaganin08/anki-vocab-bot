import { NavLink, Outlet } from "react-router-dom";

export function AdminLayout(): JSX.Element {
  return (
    <div className="admin-shell">
      <header className="app-header">
        <div className="brand-block">
          <p className="eyebrow">anki-vocab-bot</p>
          <h1>Admin Console</h1>
        </div>

        <nav className="top-nav" aria-label="Primary">
          <NavLink
            to="/"
            end
            className={({ isActive }) => (isActive ? "nav-link nav-link-active" : "nav-link")}
          >
            Dashboard
          </NavLink>
          <NavLink
            to="/cards"
            className={({ isActive }) => (isActive ? "nav-link nav-link-active" : "nav-link")}
          >
            Cards
          </NavLink>
        </nav>
      </header>

      <main className="page-shell">
        <Outlet />
      </main>
    </div>
  );
}
