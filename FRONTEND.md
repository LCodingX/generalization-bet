# Frontend Agent Specification: LLM Influence Dashboard

## Role
A Next.js 14+ (App Router) single-page application for AI safety researchers to launch fine-tuning jobs, monitor training in real time, and explore per-partition influence score matrices (TracIn + DataInf) through interactive visualizations. This is a hackathon entry — visual polish and "wow factor" matter. Judges are non-technical.

## Design System

### Visual Direction
Research-grade but visually striking. Light mode. The aesthetic is "Nature paper meets Bloomberg terminal" — data-dense but never cluttered, with smooth animation as the differentiator.

- **Background**: Slate 50 (`#f8fafc`)
- **Cards**: White (`#ffffff`), elevated with soft diffuse shadows (`0 1px 3px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.03)`), `border-radius: 12px`, `border: 1px solid #e2e8f0`
- **Typography**: DM Sans for UI, JetBrains Mono for data/code. No Inter, no Roboto, no system fonts.
- **Accent**: Indigo-500 (`#6366f1`) primary, with Indigo-800 (`#3730a3`) for emphasis
- **Partition Colors**: A fixed 10-color palette assigned by category index. Colors must be distinguishable in both line charts and heatmaps. Suggested: `["#6366f1", "#ec4899", "#14b8a6", "#f59e0b", "#8b5cf6", "#06b6d4", "#f97316", "#84cc16", "#e11d48", "#0ea5e9"]`

### Animation Principle
The wow factor is **dynamic updates**. When a new epoch's data arrives, charts don't just jump — they animate. Line charts ease new points in, heatmap cells crossfade, bar graphs grow smoothly. Use CSS transitions (0.4–0.8s ease) for most things, Recharts' built-in `isAnimationActive` for chart data, and consider Framer Motion / Motion for page transitions and card entrance animations. One well-orchestrated animation > ten scattered micro-interactions.

### Component Library
shadcn/ui for form controls (inputs, selects, switches, dialogs). Recharts for line/bar charts. Custom component for heatmaps (no good Recharts heatmap exists). Tailwind CSS for utility styling.

## Layout

Three-column structure:

```
┌──────┬─────────────────────────────────────────────┐
│      │                                             │
│ Nav  │              Main Content                   │
│ Rail │                                             │
│      │  ┌──────────────┐  ┌──────────────────────┐ │
│ Runs │  │  Left Panel  │  │    Right Panel       │ │
│ Data │  │  (Eval Qs +  │  │   (Training Data +   │ │
│ Eval │  │  Experiment  │  │    Visualizations)   │ │
│ Set- │  │   Setup)     │  │                      │ │
│ tings│  └──────────────┘  └──────────────────────┘ │
│      │                                             │
└──────┴─────────────────────────────────────────────┘
```

### Nav Rail (far left, ~68px)
- Fixed vertical strip
- Logo/icon at top (∇ gradient symbol in indigo)
- Icon buttons with tiny labels: **Runs**, **Datasets**, **Evals**, **Settings**
- Active state: indigo tinted background, indigo icon
- Inactive state: slate-400 icon

### Two-Panel Content (when viewing a run)
- **Left panel** (~35% width): Eval questions list + experiment setup (GPU, hyperparameters)
- **Right panel** (~65% width): Training data categories + visualizations

On non-run pages (Datasets, Evals, Settings), use full-width single-panel layout.

## Pages

### 1. Runs

The primary page. Three sub-tabs: **Active**, **Past**, **Queued**.

#### Run List View
Each run is a card showing:
- Run name (user-defined)
- Model name (HuggingFace ID)
- Status badge (animated pulse dot for active states)
- Progress bar (animated width transition)
- Epoch counter (e.g., "14 / 20")
- GPU type
- Created timestamp
- Click → opens Run Detail View

Status badge colors:
- `queued`: slate bg, slate text
- `training`: blue bg, blue text, pulsing dot
- `computing_tracin`: amber bg, amber text, pulsing dot
- `computing_datainf`: amber bg, amber text, pulsing dot
- `completed`: green bg, green text
- `failed`: red bg, red text

**"+ New Run" button** → opens a run creation flow (modal or dedicated view) where user selects a saved dataset, a saved eval set, a model, and configures hyperparameters.

#### Run Detail View (two-panel)

**Left Panel:**

**Eval Questions Section**
- Scrollable list of eval questions for this job
- Each item shows: index, question text, truncated completion
- Click to expand full text
- Selected eval question highlights corresponding column in heatmap (right panel)

**Experiment Setup Section** (below eval questions)
- Read-only display for active/past runs, editable for new run creation
- **Hardware**: GPU type (A100 40GB / 80GB), estimated cost
- **Basic Hyperparameters**: Learning rate, epochs, batch size, LoRA rank, LoRA alpha, max sequence length
- **Advanced** (collapsible): Checkpoint interval, DataInf damping (λ), warmup steps, weight decay, scheduler type
- Clean key-value layout, monospaced values

**Right Panel:**

**Training Categories Section**
- List of training partitions (categories) with example count per category
- Each category has its assigned color chip from the palette
- Click a category → highlights corresponding row in heatmap, filters bar graph

**Visualizations Section** (below categories, or tabbed)
- Only shown for active (partial) and completed runs
- See Visualizations section below for full detail

### 2. Datasets

CRUD interface for saved training datasets.

#### Dataset List
- Card per dataset: name, category tags (colored chips), example count, created date
- Click → view/edit
- **"+ New Dataset"** button

#### Dataset Create/Edit
- Name field
- Upload `.jsonl` file OR paste/edit inline
- Each example row: `prompt`, `completion`, `category` dropdown/tag
- Bulk category assignment (select multiple → assign category)
- Preview table with pagination
- Save → uploads to Supabase Storage + writes metadata
- **UX goal**: Make it obvious that `category` is how partitions work. Inline hint: "Categories define training partitions for influence analysis."

### 3. Evals

CRUD interface for saved eval question sets.

#### Eval List
- Card per eval set: name, question count, created date
- Click → view/edit
- **"+ New Eval Set"** button

#### Eval Create/Edit
- Name field
- Add questions one at a time or bulk paste
- Each row: `question` text + `completion` text (both required)
- Reorder via drag or index
- Inline hint: "Completions are required — the system computes gradients of the loss on these question-answer pairs."

### 4. Settings

Minimal. No credential storage for Modal/HF keys (project-owned infrastructure).

- **Display Preferences**: Theme (light only for now), chart animation speed, default sort order for scores
- **Defaults**: Default model, default LoRA rank, default checkpoint interval — pre-fill new run forms
- **Account**: User info from Supabase Auth (Google OAuth), sign out button

## Visualizations

All visualizations live in the Run Detail right panel. Two groups:

### A. Live Telemetry (Line Charts — Update During Training)

These charts grow as training progresses. When a new epoch completes, the backend writes metrics and Supabase Realtime pushes updates. The frontend appends new data points and Recharts animates the transition.

#### Plot 1: Gradient Norms
- **X axis**: Epoch (integer)
- **Y axis**: Norm of the gradient (float, ≥ 0)
- **Lines**:
  - **Bold, vibrant** primary line: `y₀ = ‖∇Φ‖` (global training gradient norm)
  - **Thin, semi-transparent** lines: `y₁…yₙ = ‖∇Φₖ‖` (per-partition gradient norms), colored by partition color palette
- **Interaction**: Hover shows tooltip with all values at that epoch. Click a legend entry to toggle partition visibility.
- **Animation**: New points ease in from the right edge (Recharts `isAnimationActive`, `animationDuration={800}`)

#### Plot 2: Local Cosine Similarity (LCS)
- **X axis**: Epoch (integer)
- **Y axis**: LCS value (float, range -1 to +1)
- **Reference line**: Horizontal dashed line at y=0
- **Lines**: Same bold/thin logic as Plot 1
- **LCS Definition** (show via info icon tooltip):
  ```
  LCS(t) = cos(v_t - v_{t-s}, v_{t+s} - v_t)
         = (v_t - v_{t-s}) · (v_{t+s} - v_t)
           / (‖v_t - v_{t-s}‖ · ‖v_{t+s} - v_t‖)

  subject to: max(‖v_t - v_{t-s}‖, ‖v_{t+s} - v_t‖) > k

  -1 = straight path, 0 = orthogonal turn, +1 = reversal
  ```
- **Delayed plot**: LCS at step t requires the gradient at step t+s (a future value). Therefore the LCS line always **trails the gradient norm line by s steps**. The trailing zone should be visually indicated — either the X axis region is lightly shaded, or the last s epochs show a dotted "pending" segment. This is mathematically inherent, not a bug. The offset `s` is derived from the checkpoint interval hyperparameter.
- **Threshold suppression**: When step-to-step gradient changes are below threshold k, LCS is undefined (suppressed). Show these as gaps in the line, not as zero.

### B. Post-Training Attributions (Static, shown after job completes. Also shown partially during `computing_datainf` phase for TracIn-only data.)

#### Heatmap (TracIn and DataInf matrices)
- **Two heatmaps**, side by side or tab-toggled: one for TracIn scores, one for DataInf scores
- **Rows**: Training categories (Φ_k)
- **Columns**: Eval questions (Γ_j), labeled by truncated question text
- **Color scale**: Diverging. White center (zero influence), deep indigo for positive, crimson for negative. Scale normalized per-matrix to the absolute max value.
- **Cell content**: Score value in small monospaced text. Bold + white text when cell intensity is high.
- **Interaction**: Hover shows full tooltip (category name, full question text, exact score). Click a cell to see the training examples in that category and the full eval question side by side.
- **Column headers**: Rotated -45° for space efficiency. Truncate to ~18 chars with ellipsis.
- **Size handling**: For ≤ 15 categories × ≤ 30 eval questions, render directly. Beyond that, add scroll with sticky row/column headers. Hackathon scale won't need virtualization.

#### Bar Graph (Aggregated Influence per Category)
- **Data**: For each training category Φ_k, sum TracIn (or DataInf) scores over all eval questions Γ_j, yielding one scalar per category.
- **Display**: Horizontal or vertical bar chart. Bars sorted descending by magnitude.
- **Two modes** (tab toggle): TracIn aggregation vs DataInf aggregation
- **Coloring**: Each bar colored by its partition color
- **Stacked variant**: Option to show a stacked bar graph where each bar is a category and the stacked segments are individual eval question contributions. This shows not just *how much* a category matters overall, but *which eval questions* it matters for.

#### Leaderboard / Rankings
- Clean ranked list below the charts
- **"Most Influential Categories"** — top 5 categories by aggregated TracIn and DataInf
- Each row: rank, category name (with color chip), TracIn aggregate, DataInf aggregate, sparkline trend if from active run
- Toggle between "by TracIn" and "by DataInf" sorting
- Clicking a category scrolls to and highlights its row in the heatmap

## Data Flow (High Level)

### Supabase Realtime (Live Updates)
- Subscribe to `jobs` table changes filtered by the active run's `job_id`
- When `progress` or `status` changes, update the run card and detail view
- For chart data: the Modal container writes epoch metrics (gradient norms, LCS values) either to a `job_metrics` table or as JSONB in the `jobs.hyperparameters` column (TBD — this needs a backend schema addition for live telemetry, separate from the final influence_scores)
- **Note**: The current backend schema stores only final `influence_scores`. Live gradient norms and LCS values during training will need either: (a) a new `job_telemetry` table with `(job_id, epoch, metric_name, metric_value)`, or (b) the Modal container sends them via the webhook callback payload and FastAPI stores them. This is the main integration gap to resolve.

### Score Fetching (Post-Training)
- `GET /api/v1/jobs/{job_id}/scores` returns the influence matrix
- Query `?category=X` for filtered views
- Query `?sort_by=tracin_score&order=desc&limit=10` for leaderboard
- Frontend transforms row data into heatmap matrix and bar chart aggregations client-side

### Dataset / Eval CRUD
- Datasets: `POST /api/v1/datasets/upload` for presigned URL, then direct upload to Supabase Storage
- Inline data: `POST /api/v1/jobs` with `training_pairs` array
- Eval sets: same pattern, stored in `eval_examples` table

## File Structure (Suggested)

```
src/
├── app/
│   ├── layout.tsx          # Root layout with sidebar nav
│   ├── page.tsx            # Redirect to /runs
│   ├── runs/
│   │   ├── page.tsx        # Run list with Active/Past/Queued tabs
│   │   ├── [id]/
│   │   │   └── page.tsx    # Run detail (two-panel with viz)
│   │   └── new/
│   │       └── page.tsx    # New run creation form
│   ├── datasets/
│   │   ├── page.tsx        # Dataset list
│   │   └── [id]/
│   │       └── page.tsx    # Dataset view/edit
│   ├── evals/
│   │   ├── page.tsx        # Eval set list
│   │   └── [id]/
│   │       └── page.tsx    # Eval set view/edit
│   └── settings/
│       └── page.tsx        # Display prefs, defaults, account
├── components/
│   ├── layout/
│   │   ├── Sidebar.tsx
│   │   └── TwoPanel.tsx
│   ├── runs/
│   │   ├── RunCard.tsx
│   │   ├── StatusBadge.tsx
│   │   ├── ProgressBar.tsx
│   │   ├── EvalQuestionsPanel.tsx
│   │   ├── ExperimentSetup.tsx
│   │   ├── TrainingCategories.tsx
│   │   └── HyperparameterForm.tsx
│   ├── viz/
│   │   ├── GradientNormsChart.tsx
│   │   ├── LCSChart.tsx
│   │   ├── InfluenceHeatmap.tsx
│   │   ├── AggregatedBarChart.tsx
│   │   ├── StackedContributions.tsx
│   │   └── Leaderboard.tsx
│   ├── datasets/
│   │   ├── DatasetCard.tsx
│   │   └── DatasetEditor.tsx
│   ├── evals/
│   │   ├── EvalCard.tsx
│   │   └── EvalEditor.tsx
│   └── ui/              # shadcn/ui components
├── lib/
│   ├── supabase.ts       # Supabase client + Realtime helpers
│   ├── api.ts            # FastAPI client wrapper
│   ├── colors.ts         # Partition color palette
│   └── types.ts          # TypeScript interfaces matching backend models
└── hooks/
    ├── useRealtimeJob.ts # Subscribe to job status changes
    ├── useScores.ts      # Fetch + transform influence scores
    └── useTelemetry.ts   # Subscribe to live training metrics
```

## Open Questions for Backend Integration
1. **Live telemetry storage**: Where do gradient norms and LCS values live between epochs? Current schema has no `job_telemetry` table. Options: (a) new table, (b) webhook payload expansion, (c) append to `jobs.hyperparameters` JSONB.
2. **LCS offset parameter `s`**: Is this a fixed value or configurable? Need to know so the frontend can correctly show the delayed region.
3. **LCS threshold `k`**: How is this set? Fixed? Per-run? Needed to know when to show gaps in the LCS plot.
4. **Heatmap at partition vs. example level**: Backend currently returns per-`train_id` scores. Are these partition-level (one row per category) or per-example? Frontend aggregation strategy depends on this.
5. **Stacked bar graph data**: Requires per-(category, eval_question) scores, which is what `influence_scores` already stores. Confirmed feasible.
