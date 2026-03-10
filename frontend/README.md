# Prism Frontend

This directory contains the React frontend for Prism, the companion application to the Data Fundamentals presentation series. The UI mirrors the product vision documented in the repository `README.md`, exposing the same canonical dataset through multiple projections.

## Tech stack

- [Vite](https://vitejs.dev/) + React + TypeScript for the application runtime and build tooling
- [Tailwind CSS](https://tailwindcss.com/) for styling (matching the clean, data-forward aesthetic described in the design doc)
- [@tanstack/react-query](https://tanstack.com/query/latest) for data fetching and caching against the FastAPI backend
- [react-router-dom](https://reactrouter.com/) for section-oriented routing (Relational, JSON, Graph, Vector, Data Entry, Prism View)
- [react-hook-form](https://react-hook-form.com/) for ingest forms
- [react-cytoscapejs](https://github.com/plotly/react-cytoscapejs) + [Cytoscape.js](https://js.cytoscape.org/) for the interactive graph projection

## Key concepts

- **Mode awareness**: A context provider tracks Demo vs Learn mode. API requests automatically append the `X-Prism-Mode` header when Learn mode is active so the backend returns SQL and pipeline metadata.
- **Authentication**: The backend requires HTTP Basic authentication. A login gate collects credentials, stores them in `sessionStorage`, and injects the `Authorization: Basic ...` header on all requests.
- **Response envelope**: API helpers unwrap the common `{ data, meta }` shape and expose both the payload and the Learn-mode metadata to the UI. Components render SQL/explain panels opportunistically when metadata is present.
- **Section layout**: Each projection is implemented as a self-contained feature module under `src/sections/`. Shared scaffolding (tabs, layout shell, learn-mode drawer) lives in `src/components/`.
- **Error tolerance**: Until all backend routes are live, each section gracefully handles `501`/`404` responses and surfaces capability gaps without crashing the app.

## Directory layout

```
frontend/
├── README.md
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
├── postcss.config.js
├── tailwind.config.ts
└── src/
    ├── main.tsx
    ├── App.tsx
    ├── styles/
    │   └── index.css
    ├── contexts/
    │   ├── AuthContext.tsx
    │   └── ModeContext.tsx
    ├── lib/
    │   ├── api-client.ts
    │   └── types.ts
    ├── hooks/
    │   └── usePrismQuery.ts
    ├── components/
    │   ├── LayoutShell.tsx
    │   ├── ModeToggle.tsx
    │   ├── SectionTabs.tsx
    │   ├── LearnPanel.tsx
    │   ├── DataTable.tsx
    │   └── ErrorState.tsx
    └── sections/
        ├── RelationalSection.tsx
        ├── JsonSection.tsx
        ├── GraphSection.tsx
        ├── VectorSection.tsx
        ├── DataEntrySection.tsx
        └── PrismViewSection.tsx
```

The remainder of this directory follows conventional Vite/Tailwind project structure. See `package.json` scripts for build/test commands.

## Getting started

1. `cd frontend`
2. `npm install`
3. `npm run dev` (launches on http://localhost:5173 by default)

Set `VITE_API_BASE_URL` in a `.env` file at the project root if the FastAPI backend is not running on `http://localhost:8000`. The frontend expects the backend routes described in `README.md` to be available and will surface helpful errors when a projection endpoint has not yet been implemented.
