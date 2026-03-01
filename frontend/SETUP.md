# LLM Influence Dashboard -- Frontend Setup

## Prerequisites

- **Node.js 18+** (verify with `node -v`)
- **npm** (ships with Node.js; verify with `npm -v`)

## Local Development Setup

```bash
git clone <repo-url>
cd generalization-bet/frontend
npm install
```

Create a `.env.local` file in the `frontend/` directory (see the next section for the required variables).

## Environment Variables

Create `frontend/.env.local` with the following:

```env
NEXT_PUBLIC_SUPABASE_URL=https://<your-project>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<your-supabase-anon-key>
NEXT_PUBLIC_API_URL=http://localhost:8000
```

| Variable | Required | Description |
|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Yes | Your Supabase project URL (found in Supabase dashboard under Project Settings > API). |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Yes | The Supabase **anon / public** key. Do **not** use the service role key here -- it is exposed to the browser. |
| `NEXT_PUBLIC_API_URL` | No | Base URL of the backend API. Defaults to `http://localhost:8000` if omitted. |

## Running Locally

```bash
npm run dev
```

The app starts at [http://localhost:3000](http://localhost:3000).

## Building for Production

```bash
npm run build
npm start
```

`npm run build` compiles the Next.js app into an optimized production bundle. `npm start` serves that bundle on port 3000.

## Deploying to Vercel

1. Push the repository to GitHub (or GitLab / Bitbucket).
2. Import the repository in the [Vercel dashboard](https://vercel.com/new).
3. Set the **Root Directory** to `frontend` if the repo contains other top-level directories.
4. Add the three environment variables listed above in Vercel's project settings (Settings > Environment Variables).
5. Deploy. Vercel auto-detects Next.js and applies the correct build settings.

Subsequent pushes to the default branch trigger automatic deployments.

## Project Structure

```
src/
  app/            Pages and layouts (Next.js App Router)
    layout.tsx      Root layout
    page.tsx        Landing / dashboard page
    datasets/       Dataset management pages
    evals/          Evaluation pages
    runs/           Job run pages
    settings/       Settings pages
  components/     Reusable UI components
    ui/             shadcn/ui primitives (Button, Card, Dialog, etc.)
    viz/            Visualization components (charts, graphs)
    datasets/       Dataset-specific components
    evals/          Eval-specific components
    layout/         Layout components (sidebar, header)
    runs/           Run-specific components
  hooks/          Custom React hooks
    useRealtimeJob.ts   Supabase Realtime subscription for live job updates
    useScores.ts        Score fetching and pagination
  lib/            Shared utilities and clients
    api.ts            Backend API client (fetch wrapper, typed endpoints)
    supabase.ts       Supabase browser client (via @supabase/ssr)
    types.ts          Shared TypeScript types
    utils.ts          General utility helpers
    colors.ts         Color constants
```

## Key Design Decisions

- **Fonts** -- DM Sans for body text, JetBrains Mono for code and numeric data.
- **Primary accent** -- Indigo-500 (`#6366f1`) used across interactive elements and charts.
- **Component library** -- [shadcn/ui](https://ui.shadcn.com/) built on Radix UI primitives and styled with Tailwind CSS v4.
- **Charts** -- [Recharts](https://recharts.org/) (v3) for all data visualizations.
- **Realtime updates** -- Supabase Realtime channels push live job-status changes to the browser via `useRealtimeJob`.
- **API layer** -- A thin typed fetch wrapper (`src/lib/api.ts`) talks to the Python backend; auth tokens are forwarded as Bearer headers.
- **Animation** -- Framer Motion for page transitions and micro-interactions.
