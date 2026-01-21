# SOAC Frontend

Production-grade React dashboard for the Self-Optimizing AI Compiler.

## Tech Stack

- React 18 + TypeScript
- Vite
- TailwindCSS
- React Router v6
- Axios
- Recharts

## Setup

```bash
cd frontend
npm install
npm run dev
```

## Pages

| Route | Description |
|-------|-------------|
| `/login` | Login with email/password or OAuth |
| `/register` | Create new account |
| `/` | Dashboard - view all jobs |
| `/new` | Create new compilation job |
| `/jobs/:id` | Job details, logs, artifacts |

## Features

- ✅ JWT authentication
- ✅ GitHub & Google OAuth
- ✅ Auto-refresh job status
- ✅ Policy-based compilation
- ✅ Reproducible build mode
- ✅ Failure simulation (demo)
- ✅ Explainability reports
- ✅ Artifact downloads
- ✅ Latency/accuracy charts

## Environment

Set `VITE_API_URL` for production deployment.
