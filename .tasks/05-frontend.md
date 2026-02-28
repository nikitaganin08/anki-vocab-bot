# Phase 5 - React Frontend

## Objective
Build a read-only admin UI that consumes backend APIs and supports browsing cards.

## Tasks
Status is tracked in `bd`; the list below is reference-only.

- 5.1 Scaffold frontend with Vite + React 18 + TypeScript.
- 5.2 Install and configure React Router + TanStack Query.
- 5.3 Create typed API client for `/api/health`, `/api/cards`, `/api/cards/{id}`, `/api/stats`.
- 5.4 Implement app layout and navigation for admin routes.
- 5.5 Implement dashboard page with counters from `/api/stats`.
- 5.6 Implement cards list page with search and filters.
- 5.7 Implement card detail page.
- 5.8 Handle loading/empty/error states consistently.
- 5.9 Configure frontend build output for backend static serving.
- 5.10 Add component tests for dashboard, list, and detail pages.

## Deliverables
- Usable read-only admin UI for card inspection.
- Components aligned with backend contracts.

## Exit Criteria
- `npm run build` succeeds.
- Admin routes render correctly when served from backend `/admin/*`.
