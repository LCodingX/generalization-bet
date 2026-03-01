# Project Context: LLM Fine-Tuning Influence Dashboard

## What We're Building
A web dashboard for AI safety researchers to fine-tune LLMs via PEFT (LoRA) and compute per-training-partition influence scores (TracIn + DataInf) against a validation question set. The goal is to help researchers build a theory of LLM generalization by seeing exactly how categories of training data affect model behavior on evaluation questions.

## Core Workflow
1. User inputs training QnA pairs (each tagged with a category like "math", "reasoning", "code") + evaluation question/answer pairs
2. System provisions a cloud GPU, runs PEFT (LoRA/QLoRA) fine-tuning
3. **Phase 1 — Online TracIn (during training):** At checkpoint intervals, gradient dot products between training partitions and eval examples are computed in-memory using only LoRA adapter gradients, accumulated into a score matrix in CPU RAM. No checkpoints saved to disk.
4. **Phase 2 — DataInf (post-training):** After training completes, influence scores are computed via closed-form Sherman-Morrison approximation (Kwon et al., ICLR 2024) at the final model state. Training examples processed one at a time to avoid OOM. Damping parameter λ is configurable.
5. Both score matrices (train_partition × eval_question) are written directly to Supabase by the GPU container
6. Frontend displays per-partition influence visualizations with both TracIn (trajectory-based) and DataInf (counterfactual) scores

## Key Difference Between the Two Methods
- **TracIn**: "How much did this training category's gradients align with reducing the eval loss *during training*?" (trajectory-based, accumulated over checkpoints)
- **DataInf**: "What would happen to the model's prediction on this eval question if we *removed* this training category?" (counterfactual, computed at final model state)

## Tech Stack
- **Frontend:** Next.js 14+ (App Router), TypeScript, Tailwind, shadcn/ui, Recharts
- **Backend:** FastAPI (Python) — thin orchestrator + webhook receiver. Never passes large data.
- **Database/Auth:** Supabase (Postgres + Auth with Google OAuth + Realtime + Storage for datasets)
- **GPU Compute:** Modal (primary) or RunPod Serverless (alternative) — cloud-only, no local workstation
- **ML:** PyTorch, HuggingFace Transformers, PEFT library, custom TracIn/DataInf computation
- **Deployment:** Vercel (frontend), Railway (FastAPI), Modal (GPU jobs)

## Database Schema
- `jobs` — lifecycle tracking (queued → provisioning → training → computing_tracin → computing_datainf → completed)
- `training_examples` — prompt, completion, **category** (partition label), job_id
- `eval_examples` — question, **completion** (required for gradient computation), job_id
- `influence_scores` — job_id, train_id, eval_id, tracin_score (float8), datainf_score (float8). Composite indexed.

## Key Architecture Decisions
- **Single Modal account**: Project-owned. Users never provide Modal/HF credentials.
- **Object storage for datasets**: Users upload to Supabase Storage; GPU containers download directly via signed URLs.
- **Async job lifecycle**: FastAPI dispatches → GPU container runs independently → container writes results directly to Supabase → frontend updates via Supabase Realtime.
- **HMAC-authenticated webhooks**: Modal container signs status callbacks; FastAPI verifies.
- **VRAM**: Minimum A100 40GB for 7B models. The binding constraint is online TracIn (simultaneous training + eval gradient computation).
- **DataInf reference**: https://github.com/ykwon0407/DataInf (ICLR 2024, `src/influence.py`)

## Target Users
AI safety researchers, likely academic, cost-sensitive, running bursty on-demand jobs.
