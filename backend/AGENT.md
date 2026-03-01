# Backend Agent Specification: LLM Influence Orchestrator

## Role
This FastAPI service is a **thin orchestrator**. It never performs ML computation. It synchronizes state between three systems: the Next.js frontend, Supabase (Postgres + Storage + Auth), and Modal (serverless GPU).

## Architecture Principles
1. **Single Modal Account**: The project owns one Modal account. Users do NOT provide their own Modal credentials. Billing is handled at the project level with per-user usage caps.
2. **FastAPI is a gateway**: It validates requests, dispatches jobs, and receives webhooks. It never passes large data payloads.
3. **GPU container writes results directly to Supabase**: Influence scores flow from Modal → Supabase, never through FastAPI.
4. **Every external endpoint is authenticated**: JWT for user-facing routes, HMAC for webhook callbacks.

## Influence Computation Architecture

The GPU container runs a **two-phase** influence computation pipeline. These two methods measure different things and are always computed together per job.

### Phase 1: Online TracIn (During Training)

TracIn (Pruthi et al., 2020) measures how each training partition's gradient aligns with the evaluation loss across the training trajectory. The core formula:

```
TracIn(z_train, z_eval) = Σ_t η_t ( ∇L(w_t, z_train) · ∇L(w_t, z_eval) )
```

**Computed online, in-memory, during the fine-tuning loop. No checkpoints saved to disk.**

Pipeline:
1. Pre-load all eval examples (questions + completions) and training set (partitioned by category Φ_A, Φ_B, ...) into GPU memory before training starts.
2. At designated checkpoint intervals (e.g., every 50 steps), pause the training update.
3. Run forward/backward pass on each eval example to get ∇L_eval for each eval question Γ_j.
4. Run forward/backward pass on each training partition to get ∇L_train for each partition Φ_k, as well as the global training set gradient ∇L_train(Φ).
5. Compute dot products between each training partition gradient and each eval question gradient. This yields matrix M where M[k,j] = ∇L_train(Φ_k) · ∇L_eval(Γ_j).
6. Add these scalar values to a running total matrix in CPU RAM (not GPU VRAM).
7. Zero out gradients and resume training.
8. Use ∇L_train(Φ) (global training gradient) to update θ for this timestep.

**LoRA multiplier**: Only track gradients of LoRA adapter matrices (A and B tensors), NOT the frozen base model. This reduces gradient dimensionality from billions to ~2-4M parameters, making dot products near-instantaneous.

By the time fine-tuning finishes, the TracIn score matrix is already complete in CPU RAM.

### Phase 2: DataInf (Post-Training)

DataInf (Kwon et al., 2023, ICLR 2024) approximates the classical influence function using a closed-form expression based on the Sherman-Morrison formula. It operates on the **final trained model only** — it is NOT accumulated during training.

**Reference**: https://arxiv.org/pdf/2310.00902

The DataInf formula per layer l:

```
I_DataInf(z_train, z_eval) = -Σ_l ∇θ_l ℓ(z_train)^T × (1/(nλ_l) × Σ_i U_{l,i}) × ∇θ_l ℓ(z_eval)

where U_{l,i} = I_{d_l} - (∇θ_l ℓ_i × ∇θ_l ℓ_i^T) / (λ_l + ||∇θ_l ℓ_i||²)
```

Pipeline (runs AFTER training completes):
1. Freeze the final model (base + trained LoRA adapters).
2. For each training example i, compute per-example gradient ∇θ_l ℓ_i for each LoRA layer l. **Process one example at a time** to avoid OOM — store gradient vector in CPU RAM, free GPU memory immediately. Do NOT batch all training gradients into GPU memory.
3. Compute U_{l,i} for each training example using the Sherman-Morrison formula (closed-form, no matrix inversion needed).
4. For each eval example, compute ∇θ_l ℓ(z_eval) and apply the accumulated DataInf operator.
5. This yields a score matrix of the same shape as TracIn: one scalar per (train_partition, eval_question) pair.

**Damping parameter λ (lambda)**: Controls regularization in the Sherman-Morrison approximation. Exposed as a job hyperparameter `datainf_damping` with default 0.1. The approximation error scales as O(d_l²) where d_l is the per-layer parameter count — with LoRA's small d_l, error is well-bounded.

**Key difference from TracIn**: DataInf captures the counterfactual influence of removing a training point on the model's prediction (based on the final model state), while TracIn captures how much a training point contributed to reducing the eval loss during training (trajectory-based). Showing both gives researchers two complementary lenses on the same data.

**Reference implementation**: https://github.com/ykwon0407/DataInf — specifically `src/influence.py` for the core computation.

### VRAM Requirements

The binding constraint is the online TracIn step, which must hold simultaneously:
- Base model (frozen, 8-bit quantized): ~7 GB for 7B model
- LoRA adapters (trainable): ~50-200MB depending on rank
- Training batch activations + gradients: ~2-4GB
- Eval set forward/backward pass (during TracIn callback): ~1-3GB depending on eval set size
- Optimizer states: ~200-500MB (LoRA params only)

**Minimum**: A100 40GB for 7B models with LoRA rank ≤ 32 and ≤ 100 eval questions.
**Recommended**: A100 80GB for comfortable headroom or larger models.
**Not sufficient**: 24GB GPUs (RTX 4090, L4) will be too tight for the simultaneous training + eval gradient computation.

For the DataInf post-training phase, VRAM pressure is lower since we process examples one at a time.

## Database Schema (Supabase Postgres)
See `schema.sql` for the full migration. Four core tables:

### `jobs`
Tracks the lifecycle of a fine-tuning + influence computation run.
- `id` (uuid, PK)
- `user_id` (uuid, FK → auth.users)
- `status` (text: queued | provisioning | training | computing_tracin | computing_datainf | completed | failed)
- `status_message` (text, nullable — human-readable detail on failure)
- `progress` (float, 0.0–1.0)
- `model_name` (text — HuggingFace model ID, e.g. "meta-llama/Llama-2-7b-hf")
- `hyperparameters` (jsonb — learning_rate, epochs, lora_rank, lora_alpha, checkpoint_interval, datainf_damping, etc.)
- `dataset_storage_path` (text — path in Supabase Storage bucket)
- `modal_call_id` (text, nullable — returned by modal spawn())
- `started_at` (timestamptz, nullable)
- `completed_at` (timestamptz, nullable)
- `created_at` (timestamptz, default now())

### `training_examples`
- `id` (uuid, PK)
- `job_id` (uuid, FK → jobs.id ON DELETE CASCADE)
- `index` (integer — ordering within the dataset)
- `category` (text — partition label, e.g. "math", "reasoning", "code". Training examples are grouped by category for partition-level influence computation.)
- `prompt` (text)
- `completion` (text)

### `eval_examples`
- `id` (uuid, PK)
- `job_id` (uuid, FK → jobs.id ON DELETE CASCADE)
- `index` (integer)
- `question` (text)
- `completion` (text — required for computing loss and gradients on eval examples)

### `influence_scores`
The output matrix. For K training partitions and M eval questions, this holds K×M rows per job.
- `id` (uuid, PK)
- `job_id` (uuid, FK → jobs.id ON DELETE CASCADE)
- `train_id` (uuid, FK → training_examples.id)
- `eval_id` (uuid, FK → eval_examples.id)
- `tracin_score` (float8) — scalar: cumulative gradient dot product over training trajectory
- `datainf_score` (float8) — scalar: closed-form influence approximation at final model
- Composite index on `(job_id, train_id)`
- Composite index on `(job_id, eval_id)`
- Unique constraint on `(job_id, train_id, eval_id)`

## API Routes

### User-Facing (JWT-authenticated)

#### `POST /api/v1/jobs`
Create a new fine-tuning + influence computation job.
- Input: `{ model_name, hyperparameters, training_pairs: [{prompt, completion, category}], eval_examples: [{question, completion}], dataset_file_id? }`
- If `training_pairs` array is provided and small (<2MB), write rows to `training_examples` directly.
- If `dataset_file_id` is provided, it references an already-uploaded file in Supabase Storage.
- Creates the job row with status `queued`.
- Dispatches to Modal via `spawn()` (spawn returns immediately).
- Returns `{ job_id, status: "queued" }`.

#### `GET /api/v1/jobs`
List all jobs for the authenticated user. Supports `?status=completed` filtering.

#### `GET /api/v1/jobs/{job_id}`
Get job details including status and progress.

#### `GET /api/v1/jobs/{job_id}/scores`
Get influence score matrix. Supports query params:
- `?train_id=uuid` — scores for a specific training example across all eval questions
- `?eval_id=uuid` — scores for a specific eval question across all training examples
- `?category=math` — scores for all examples in a category across all eval questions
- `?sort_by=tracin_score&order=desc&limit=20` — top influential examples/partitions

#### `POST /api/v1/datasets/upload`
Get a presigned upload URL for Supabase Storage. Frontend uploads directly to Storage using this URL. Returns `{ upload_url, storage_path }`.

#### `DELETE /api/v1/jobs/{job_id}`
Cancel a job. If running, attempts to cancel via Modal. Deletes all associated data (CASCADE).

### Webhook (HMAC-authenticated)

#### `POST /api/v1/callbacks/job-update`
Called by the Modal GPU container to report status changes.
- Headers: `X-Webhook-Signature: hmac-sha256=<hex_digest>`
- Payload: `{ job_id, status, progress?, status_message? }`
- Validates HMAC using `WEBHOOK_SECRET` (shared between FastAPI and Modal container).
- Updates the `jobs` table. Supabase Realtime pushes the change to the frontend automatically.

## Modal Dispatch Logic

```python
import modal

# Project-level Modal auth (from env vars MODAL_TOKEN_ID, MODAL_TOKEN_SECRET)
# Modal SDK reads these automatically — no Client.from_credentials() needed.

f = modal.Function.lookup("tracin-runner", "train_and_compute_influence")

call = f.spawn(
    dataset_url=signed_url,          # Supabase Storage signed URL
    eval_examples=eval_examples,     # List of {question, completion} — small, fine to pass
    config=job_hyperparameters,       # Dict including datainf_damping, checkpoint_interval
    job_id=str(job_id),              # So the container can write back
    supabase_url=SUPABASE_URL,       # Container writes results directly
    supabase_service_key=SUPABASE_SERVICE_KEY,  # Service role for direct DB writes
    callback_url=CALLBACK_URL,       # Webhook URL for status updates
    webhook_secret=WEBHOOK_SECRET,   # For HMAC signing
)

# Store the call ID for potential cancellation or fallback polling
update_job(job_id, modal_call_id=call.object_id)
```

## What the Modal Container Does (NOT this backend's responsibility)

### Phase 1: Setup
1. Downloads dataset from signed URL
2. Loads base model in 4-bit quantization + creates LoRA adapters via PEFT
3. Parses training data into partitions by `category` field
4. Pre-loads all eval examples (questions + completions) into memory
5. Sends webhook: `status=training`

### Phase 2: Fine-tuning + Online TracIn
6. Runs training loop with TracIn callback at every `checkpoint_interval` steps:
   - Pauses training
   - Computes per-partition training gradients (LoRA params only)
   - Computes per-eval-question gradients (LoRA params only)
   - Computes dot product matrix, adds to running totals in CPU RAM
   - Zeros gradients, resumes training with global training gradient
7. TracIn score matrix is complete when training finishes
8. Sends webhook: `status=computing_datainf`

### Phase 3: DataInf (Post-Training)
9. Freezes final model (base + trained LoRA)
10. Iterates over training examples ONE AT A TIME:
    - Computes per-example gradient for each LoRA layer
    - Computes U_{l,i} via Sherman-Morrison (closed-form, no inversion)
    - Stores gradient + U in CPU RAM, frees GPU memory
11. For each eval example, applies the accumulated DataInf operator
12. DataInf score matrix complete

### Phase 4: Write Results
13. Writes all rows to `influence_scores` table via Supabase service key
14. Sends final webhook: `status=completed, progress=1.0`

## Security
- **JWT Verification**: Every user-facing route validates the Supabase JWT using the project's JWT secret via PyJWT. Extracts `user_id` from the `sub` claim.
- **Webhook HMAC**: The Modal container signs callback payloads with `WEBHOOK_SECRET` using HMAC-SHA256. FastAPI verifies before processing.
- **No credential storage**: Users never provide Modal or HF tokens. The project owns the infrastructure.
- **Row-Level Security**: Supabase RLS policies ensure users can only read their own jobs and scores. The service role key (used by Modal container) bypasses RLS for writes.
- **HuggingFace Token**: Stored as a project-level env var in Modal, not per-user. If gated models are needed, the project's HF account must have access.

## Stale Job Recovery
A scheduled task (Supabase Edge Function or external cron hitting a protected endpoint) runs every 15 minutes:
- Finds jobs with status `running`/`training`/`computing_*` and `updated_at` older than the configured timeout.
- Uses `modal.functions.FunctionCall.from_id(modal_call_id)` to check actual status.
- Marks truly dead jobs as `failed` with an appropriate message.

## Environment Variables
```
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...           # Service role key (server-side only)
SUPABASE_JWT_SECRET=your-jwt-secret   # For verifying user JWTs
MODAL_TOKEN_ID=ak-...                 # Project Modal account
MODAL_TOKEN_SECRET=as-...             # Project Modal account
WEBHOOK_SECRET=a-random-64-char-hex   # Shared with Modal container
HF_TOKEN=hf_...                       # Project HuggingFace token
CALLBACK_BASE_URL=https://your-api.railway.app
```
