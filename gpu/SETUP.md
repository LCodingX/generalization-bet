# GPU Container Setup

Modal-based GPU container for TracIn + DataInf influence score computation.

## Prerequisites

- Python 3.11+
- [Modal CLI](https://modal.com/docs/guide) installed and authenticated
- HuggingFace token (for gated models like Llama-2)

## Local Development

```bash
cd gpu

# Install dependencies
pip install -r requirements.txt

# Run tests (all tests run on CPU, no GPU needed)
pytest tests/ -v
```

## Deploy to Modal

```bash
cd gpu
modal deploy app.py
```

Verify `tracin-runner` appears in your [Modal dashboard](https://modal.com/apps).

## Configuration

The function is looked up as `modal.Function.lookup("tracin-runner", "train_and_compute_influence")`.

GPU: A100 80GB, 32GB system RAM, 6h timeout, no retries.

## Architecture

```
Backend (FastAPI)
    │
    ├── f.spawn(dataset_url, eval_examples, config, ...)
    │
    ▼
Modal Container (this code)
    │
    ├── 1. Provisioning: Load model + data
    ├── 2. Training + TracIn: Fine-tune with LoRA, checkpoint influence
    ├── 3. DataInf: 3-pass streaming Sherman-Morrison
    ├── 4. Write scores: Batch upsert to Supabase
    │
    ├── Webhooks → Backend (HMAC-signed status updates)
    └── Scores  → Supabase (direct write via service key)
```

## Status Flow

`provisioning` → `training` → `computing_tracin` → `computing_datainf` → `completed`

Any failure sends `failed` status then re-raises.

## Monitoring

- Modal dashboard: View container logs, GPU utilization
- Backend: `/api/v1/admin/health` for stale job recovery
- Supabase: Check `influence_scores` table for results

## Troubleshooting

- **OOM**: Reduce `batch_size` or `max_seq_length` in job hyperparameters
- **Timeout**: 6h limit. For large datasets, reduce `epochs`
- **Model not found**: Ensure HF token has access to gated models
- **Webhook failures**: Non-fatal. Backend has stale job recovery (30min timeout)
