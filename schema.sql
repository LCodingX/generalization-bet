-- ============================================================
-- Supabase Schema: LLM Influence Dashboard
-- Run this in the Supabase SQL Editor
-- ============================================================

-- Enable UUID generation
create extension if not exists "uuid-ossp";

-- ============================================================
-- TABLES
-- ============================================================

create table public.jobs (
    id uuid primary key default uuid_generate_v4(),
    user_id uuid not null references auth.users(id) on delete cascade,
    status text not null default 'queued'
        check (status in ('queued','provisioning','training','computing_tracin','computing_datainf','completed','failed')),
    status_message text,
    progress float not null default 0.0
        check (progress >= 0.0 and progress <= 1.0),
    model_name text not null,
    hyperparameters jsonb not null default '{}',
    dataset_storage_path text,
    modal_call_id text,
    telemetry jsonb not null default '[]',
    started_at timestamptz,
    completed_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table public.training_examples (
    id uuid primary key default uuid_generate_v4(),
    job_id uuid not null references public.jobs(id) on delete cascade,
    index integer not null,
    category text not null default 'default',
    prompt text not null,
    completion text not null
);

create table public.eval_examples (
    id uuid primary key default uuid_generate_v4(),
    job_id uuid not null references public.jobs(id) on delete cascade,
    index integer not null,
    question text not null,
    completion text not null
);

create table public.influence_scores (
    id uuid primary key default uuid_generate_v4(),
    job_id uuid not null references public.jobs(id) on delete cascade,
    train_id uuid not null references public.training_examples(id) on delete cascade,
    eval_id uuid not null references public.eval_examples(id) on delete cascade,
    tracin_score float8 not null default 0.0,
    datainf_score float8 not null default 0.0
);

-- ============================================================
-- INDEXES
-- ============================================================

create index idx_jobs_user_id on public.jobs(user_id);
create index idx_jobs_status on public.jobs(status);
create index idx_training_examples_job_id on public.training_examples(job_id);
create index idx_training_examples_category on public.training_examples(job_id, category);
create index idx_eval_examples_job_id on public.eval_examples(job_id);
create index idx_influence_scores_job_train on public.influence_scores(job_id, train_id);
create index idx_influence_scores_job_eval on public.influence_scores(job_id, eval_id);
create unique index idx_influence_scores_unique on public.influence_scores(job_id, train_id, eval_id);

-- ============================================================
-- AUTO-UPDATE updated_at
-- ============================================================

create or replace function public.handle_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

create trigger on_jobs_updated
    before update on public.jobs
    for each row execute function public.handle_updated_at();

-- ============================================================
-- ROW LEVEL SECURITY
-- ============================================================

alter table public.jobs enable row level security;
alter table public.training_examples enable row level security;
alter table public.eval_examples enable row level security;
alter table public.influence_scores enable row level security;

-- Users can read/insert/delete their own jobs
create policy "Users manage own jobs"
    on public.jobs for all
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);

-- Users can read training examples for their own jobs
create policy "Users read own training examples"
    on public.training_examples for select
    using (exists (
        select 1 from public.jobs where jobs.id = training_examples.job_id and jobs.user_id = auth.uid()
    ));

-- Users can insert training examples for their own jobs
create policy "Users insert own training examples"
    on public.training_examples for insert
    with check (exists (
        select 1 from public.jobs where jobs.id = training_examples.job_id and jobs.user_id = auth.uid()
    ));

-- Users can read eval examples for their own jobs
create policy "Users read own eval examples"
    on public.eval_examples for select
    using (exists (
        select 1 from public.jobs where jobs.id = eval_examples.job_id and jobs.user_id = auth.uid()
    ));

-- Users can insert eval examples for their own jobs
create policy "Users insert own eval examples"
    on public.eval_examples for insert
    with check (exists (
        select 1 from public.jobs where jobs.id = eval_examples.job_id and jobs.user_id = auth.uid()
    ));

-- Users can read influence scores for their own jobs
create policy "Users read own influence scores"
    on public.influence_scores for select
    using (exists (
        select 1 from public.jobs where jobs.id = influence_scores.job_id and jobs.user_id = auth.uid()
    ));

-- ============================================================
-- REALTIME (enable for frontend subscriptions)
-- ============================================================

alter publication supabase_realtime add table public.jobs;

-- ============================================================
-- STORAGE BUCKET
-- ============================================================
-- Run separately or via Supabase dashboard:
-- insert into storage.buckets (id, name, public) values ('datasets', 'datasets', false);
