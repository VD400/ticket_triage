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
