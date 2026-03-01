# Changelog: Backend v0.2.0 — DataInf/TracIn Architecture Update

## Summary
Updated the entire backend to properly separate the two-phase influence computation pipeline, add DataInf-specific details, fix schema gaps, and align with the partitioned training set design.

## AGENT.md (Major Rewrite)
**Added:**
- Full "Influence Computation Architecture" section with two clearly separated phases
- Phase 1: Online TracIn pipeline (7-step in-memory computation during training)
- Phase 2: DataInf pipeline (5-step post-training computation with Sherman-Morrison formula)
- Complete DataInf formula with U_{l,i} closed-form expression
- Explanation of damping parameter λ and its role
- Key difference between TracIn (trajectory-based) and DataInf (counterfactual)
- VRAM requirements section with specific GPU sizing (A100 40GB minimum, 80GB recommended)
- Warning that 24GB GPUs are insufficient for simultaneous training + eval gradient computation
- Reference to DataInf GitHub repo and ICLR 2024 paper
- Note that DataInf processes training examples ONE AT A TIME to avoid OOM
- Explicit note that `completion` on eval_examples is required for gradient computation

**Changed:**
- `eval_questions: [string]` → `eval_examples: [{question, completion}]` in API input
- Added `category` field to training examples throughout
- Added `datainf_damping` to hyperparameters
- Added `?category=math` filter to scores endpoint
- Modal dispatch now passes `eval_examples` (with completions) instead of `eval_questions`
- Container pipeline expanded from 6 steps to 4 phases / 15 steps

## schema.sql
**Added:**
- `category text not null default 'default'` column to `training_examples`
- `completion text not null` column to `eval_examples`
- `idx_training_examples_category` composite index on `(job_id, category)`

## models.py
**Added:**
- `category` field to `TrainingPair` model (default: "default")
- `EvalExample` model with `question` + `completion` fields
- `datainf_damping` field to `Hyperparameters` (default: 0.1, range: 0-10)
- `category` filter to `ScoresQuery` model
- `train_category` field to `InfluenceScoreRow` response model

**Changed:**
- `CreateJobRequest.eval_questions: list[str]` → `eval_examples: list[EvalExample]`
- Validator renamed from `eval_questions_non_empty` → `eval_examples_non_empty`
- Validator now checks both `question` and `completion` are non-empty

## supabase_client.py
**Changed:**
- `insert_training_examples()` now includes `category` field in inserted rows
- `insert_eval_examples()` renamed param from `questions: list[str]` → `examples: list[dict]`, now inserts `completion`
- `get_influence_scores()` added `category` parameter, queries `training_examples.category` in filter
- Score query join now includes `category` in the select: `training_examples!inner(index, category, prompt)`

## modal_dispatch.py
**Changed:**
- `dispatch_job()` parameter renamed from `eval_questions: list[str]` → `eval_examples: list[dict]`
- `f.spawn()` call passes `eval_examples` instead of `eval_questions`

## routes/jobs.py
**Changed:**
- `create_job()` now serializes inline data with `category` field
- Eval examples insert uses `[ex.model_dump() for ex in body.eval_examples]` instead of raw strings
- Modal dispatch passes `eval_examples` dicts with completions
- `get_scores()` endpoint accepts `category` query parameter
- Score row construction now includes `train_category` from joined data

## PROJECT_CONTEXT.md
**Rewritten** to reflect two-phase architecture, category-based partitions, eval completions, and DataInf specifics.
