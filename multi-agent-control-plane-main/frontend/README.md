# RL Decision Brain Frontend (Next.js)

Production-style dashboard frontend for RL Decision Brain + Multi-Agent Control Plane integration.

## Stack

- Next.js 14 (App Router)
- React 18
- TypeScript
- Tailwind CSS

## Run locally

1. Install dependencies:

```bash
npm install
```

2. Start dev server:

```bash
npm run dev
```

Frontend runs on `http://localhost:3200`.

To use a different frontend port:

```powershell
npm run dev -- -p 3300
```

## Backend dependency

Set API base in `.env.local`:

```bash
NEXT_PUBLIC_BACKEND_PORT=7999
NEXT_PUBLIC_DECISION_BRAIN_API_URL=http://localhost:7999
```

`NEXT_PUBLIC_DECISION_BRAIN_API_URL` takes priority. If omitted, frontend uses `http://localhost:${NEXT_PUBLIC_BACKEND_PORT}`.

The frontend consumes live backend endpoints via `lib/api.ts`, including:

- `/health`
- `/action-scope`
- `/recent-activity`
- `/decision-summary`
- `/decision`
- `/decision-with-control-plane`
- `/live-dashboard`
- `/ingest-link`
- `/remove-link`
- `/control-plane/status`
- `/control-plane/apps`
- `/orchestration/metrics`

## Notes

- Home dashboard and Decision Brain page poll backend data for near real-time updates.
- If API is unreachable, UI shows fallback/error state while retaining the current view.
