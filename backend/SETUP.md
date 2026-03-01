# LLM Influence Orchestrator -- Backend Setup

FastAPI backend that orchestrates PEFT fine-tuning jobs on Modal and serves TracIn + DataInf influence scores to the frontend.

---

## 1. Prerequisites

- **Python 3.11+** -- The Dockerfile and dependencies target Python 3.11.
- **Supabase project** -- Free tier works. You need the project URL, service role key, and JWT secret.
- **Modal account** -- Sign up at [modal.com](https://modal.com). You need a project-level API token (not per-user).
- **HuggingFace account** -- Create an access token at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) with read access to gated models (e.g., Llama 2).

---

## 2. Local Development Setup

```bash
# Clone the repository (if you haven't already)
git clone <repo-url>
cd generalization-bet/backend

# Create and activate a virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create your .env file from the example
cp .env.example .env
# Then fill in each value -- see section 5 for details
```

---

## 3. Supabase Configuration

### 3.1 Run the schema migration

1. Open your Supabase project dashboard.
2. Navigate to **SQL Editor**.
3. Paste the contents of `schema.sql` (located at the repository root) and run it.

This creates the following tables with RLS policies, indexes, and triggers:

- `jobs` -- tracks fine-tuning job lifecycle
- `training_examples` -- prompt/completion pairs per job
- `eval_examples` -- evaluation questions per job
- `influence_scores` -- TracIn and DataInf scores linking training to eval examples

### 3.2 Create the storage bucket

1. Go to **Storage** in the Supabase dashboard.
2. Click **New bucket**.
3. Name it `datasets`.
4. Set it to **private** (not public).

Alternatively, run this SQL:

```sql
INSERT INTO storage.buckets (id, name, public) VALUES ('datasets', 'datasets', false);
```

### 3.3 Enable Realtime on the jobs table

The schema migration already runs:

```sql
ALTER PUBLICATION supabase_realtime ADD TABLE public.jobs;
```

Verify Realtime is enabled by checking **Database > Replication** in the dashboard and confirming the `jobs` table is listed.

### 3.4 Get your credentials

From the Supabase dashboard, go to **Project Settings > API**:

- **Project URL** -- This is your `SUPABASE_URL`.
- **Service role key** (under "Project API keys") -- This is your `SUPABASE_SERVICE_KEY`. Keep it secret; it bypasses Row Level Security.
- **JWT Secret** (under "JWT Settings") -- This is your `SUPABASE_JWT_SECRET`. Used by the backend to verify user JWTs from the frontend.

---

## 4. Modal Setup

```bash
# Install the Modal CLI (included in requirements.txt, but also available standalone)
pip install modal

# Authenticate and generate a token
modal token new
```

This opens a browser window. After authenticating, Modal stores the token locally. Copy the token ID and secret from your Modal dashboard (**Settings > API Tokens**) into your `.env`:

```
MODAL_TOKEN_ID=ak-xxxxxxxxxxxx
MODAL_TOKEN_SECRET=as-xxxxxxxxxxxx
```

These are project-level credentials, not per-user tokens. The Modal SDK also reads them from the environment automatically, but the backend validates their presence at startup.

---

## 5. Environment Variables

Create a `.env` file from `.env.example`. Every variable is **required**.

| Variable | Description |
|---|---|
| `SUPABASE_URL` | Your Supabase project URL, e.g. `https://abcdefgh.supabase.co` |
| `SUPABASE_SERVICE_KEY` | Service role key from Supabase. Server-side only; bypasses RLS. Never expose to the client. |
| `SUPABASE_JWT_SECRET` | JWT secret from Supabase project settings. Used to verify user access tokens sent by the frontend. |
| `MODAL_TOKEN_ID` | Modal API token ID, starts with `ak-`. |
| `MODAL_TOKEN_SECRET` | Modal API token secret, starts with `as-`. |
| `WEBHOOK_SECRET` | A 64-character hex string used for HMAC verification of callbacks from Modal containers. Generate with the command in section 10. |
| `CALLBACK_BASE_URL` | The publicly reachable URL of this backend, e.g. `https://your-api.railway.app`. Modal containers POST status updates to `{CALLBACK_BASE_URL}/api/v1/callbacks/job-update`. For local dev, use a tunnel like ngrok. |
| `HF_TOKEN` | HuggingFace access token, starts with `hf_`. Needs read access to any gated models you plan to fine-tune. |

The following have defaults and are optional in `.env`:

| Variable | Default | Description |
|---|---|---|
| `MODAL_APP_NAME` | `tracin-runner` | Name of the Modal app to invoke. |
| `MODAL_FUNCTION_NAME` | `train_and_compute_influence` | Name of the Modal function within the app. |
| `MAX_TRAINING_EXAMPLES` | `5000` | Max training examples allowed in a single inline request. |
| `MAX_EVAL_EXAMPLES` | `100` | Max eval examples per job. |
| `MAX_INLINE_PAYLOAD_BYTES` | `2000000` | Max size (bytes) for inline training data. Larger datasets must be uploaded as files. |
| `JOB_TIMEOUT_MINUTES` | `360` | Minutes before a stale job is eligible for recovery (6 hours). |

---

## 6. Running Locally

```bash
# Make sure your .env is populated and your venv is active
uvicorn app.main:app --reload --port 8000
```

The API will be available at:

- **Root**: http://localhost:8000/ -- returns service name and version
- **Swagger UI**: http://localhost:8000/docs -- interactive API documentation
- **ReDoc**: http://localhost:8000/redoc -- alternative documentation view

Note: For Modal callbacks to reach your local machine during development, you need a publicly accessible URL. Use a tunneling tool like [ngrok](https://ngrok.com):

```bash
ngrok http 8000
```

Then set `CALLBACK_BASE_URL` in your `.env` to the ngrok HTTPS URL.

---

## 7. Docker

### Build

```bash
docker build -t llm-influence-orchestrator .
```

### Run

```bash
docker run -p 8000:8000 --env-file .env llm-influence-orchestrator
```

The container runs `uvicorn app.main:app --host 0.0.0.0 --port 8000` and exposes port 8000.

---

## 8. Deploying to Railway

1. **Connect your repository** -- In the Railway dashboard, create a new project and connect the GitHub repo. Point the service to the `backend/` directory (or the repo root if the backend is at the root).

2. **Set environment variables** -- Go to the service's **Variables** tab and add every variable from section 5. Do not upload your `.env` file directly; paste each key-value pair.

3. **Railway auto-detects the Dockerfile** -- No additional build configuration is needed. Railway will build and deploy using the `Dockerfile` in the backend directory.

4. **Set the public domain** -- Under **Settings > Networking**, generate a Railway domain or attach a custom domain. Use this URL as your `CALLBACK_BASE_URL`.

5. **Verify** -- After deployment, hit `https://your-app.railway.app/` to confirm the service is running. Check `/docs` for the Swagger UI.

---

## 9. Testing the API

### Health check

```bash
curl http://localhost:8000/
```

Expected response:

```json
{
  "service": "llm-influence-orchestrator",
  "version": "0.1.0",
  "docs": "/docs"
}
```

### Create a job

All job endpoints require a valid Supabase JWT in the `Authorization` header. The frontend obtains this token via Supabase Auth; for manual testing, you can get one from your Supabase project's auth flow or generate one using the JWT secret.

```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <YOUR_SUPABASE_JWT>" \
  -d '{
    "model_name": "meta-llama/Llama-2-7b-hf",
    "hyperparameters": {
      "learning_rate": 2e-4,
      "epochs": 3,
      "lora_rank": 16
    },
    "training_pairs": [
      {
        "prompt": "What is the capital of France?",
        "completion": "The capital of France is Paris.",
        "category": "geography"
      }
    ],
    "eval_examples": [
      {
        "question": "Name the capital of Germany.",
        "completion": "The capital of Germany is Berlin."
      }
    ]
  }'
```

Expected response (HTTP 201):

```json
{
  "job_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "status": "provisioning"
}
```

### Check job status

```bash
curl http://localhost:8000/api/v1/jobs/<JOB_ID> \
  -H "Authorization: Bearer <YOUR_SUPABASE_JWT>"
```

### List all jobs

```bash
curl http://localhost:8000/api/v1/jobs \
  -H "Authorization: Bearer <YOUR_SUPABASE_JWT>"
```

### Get influence scores (after job completes)

```bash
curl "http://localhost:8000/api/v1/jobs/<JOB_ID>/scores?sort_by=tracin_score&order=desc&limit=10" \
  -H "Authorization: Bearer <YOUR_SUPABASE_JWT>"
```

### Delete a job

```bash
curl -X DELETE http://localhost:8000/api/v1/jobs/<JOB_ID> \
  -H "Authorization: Bearer <YOUR_SUPABASE_JWT>"
```

---

## 10. Webhook Secret Generation

The webhook secret is a shared HMAC key between the backend and Modal containers. Generate one with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

This produces a 64-character hex string. Set it as `WEBHOOK_SECRET` in your `.env` and configure the same value in your Modal container environment so that callback payloads can be verified.
