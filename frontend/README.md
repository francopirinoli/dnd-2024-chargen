<!-- markdownlint-disable-file -->
# Frontend (React SPA)

Vite + React + TypeScript + Tailwind + shadcn/ui scaffold for the D&D 2024 Character Creator.

## Stack

- Vite (build, dev server)
- React 18 + TypeScript
- Tailwind CSS with shadcn/ui design tokens (dark mode + red/gold brand palette)
- Zustand (UI state only — character data is authoritative on the Flask API)
- TanStack Query (server-state cache for the API)
- React Router
- vite-plugin-pwa (installable on mobile)
- Cinzel (display) + Inter (body) via `@fontsource`

## Develop

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173 (proxies /api -> http://localhost:5000)
```

In another terminal, run the Flask API:

```bash
python app.py        # http://localhost:5000
```

## Build

```bash
npm run build        # outputs to frontend/dist
```
