# React + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and [`typescript-eslint`](https://typescript-eslint.io) in your project.

## Dashboard synchronization checks

The dashboard shares ticket data across its pages, receives WebSocket notifications,
and refreshes every five seconds as a fallback. Live Trace includes active and
resolved tickets, persisted event history, and expandable drafts and resolutions.

Run the browser regression tests from `frontend`:

```bash
npm ci
npx playwright install chromium
npm run test:e2e
```

These tests use mocked API and WebSocket responses, so they do not need a running
backend or provider keys. They cover complaint submission across browser tabs,
worker progress, review and resolution, reconnecting, history deduplication, and
mobile ticket selection. GitHub Actions runs them with the frontend checks.

## Recover interrupted complaints

A database ticket can outlive its Redis job after an abrupt shutdown or Redis
reset. The age shown in the queue is the complaint's creation time, not a worker
runtime. Expand a failed ticket or a queued/processing ticket with no activity
for ten minutes and click **Retry processing** as an admin or agent.

Keep Redis, the backend and the worker running. Recovery continues its saved
checkpoint, restores an existing draft to review, or restores a saved human
question to Needs attention. A completed saved resolution returns to Resolved.
If there is no checkpoint, the worker starts processing from the complaint.
The original complaint and event history remain intact. Retrying can make new
provider calls for unfinished steps.

Restart every worker after updating the code so duplicate jobs share the
PostgreSQL guard. Recovery does not need new environment variables or migrations.
