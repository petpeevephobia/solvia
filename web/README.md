# Solvia Web (React + TypeScript)

This folder will contain the React frontend for Solvia v2.

## Tech Stack
- React 18
- TypeScript
- Vite
- TailwindCSS
- React Query (TanStack)
- Zustand (state management)

## Structure (Planned)
```
src/
├── components/
│   ├── ui/           # Button, Input, Card, Modal
│   ├── layout/       # Sidebar, Header, Footer
│   └── charts/       # LineChart, BarChart
├── features/
│   ├── auth/         # Login, OAuth callback
│   ├── dashboard/    # Main dashboard
│   ├── audit/        # SEO audits
│   ├── gsc/          # Google Search Console
│   ├── chat/         # AI assistant
│   └── onpage/       # On-page SEO analysis
├── hooks/            # Custom hooks
├── services/         # API clients
├── stores/           # Zustand stores
├── types/            # TypeScript types
└── utils/            # Helper functions
```

## Setup (Coming Soon)
```bash
npm install
npm run dev
```

## Build
```bash
npm run build
```
