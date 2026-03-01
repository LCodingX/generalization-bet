// ============================================================
// Types matching backend API models
// ============================================================

export type JobStatus =
  | "queued"
  | "provisioning"
  | "training"
  | "computing_tracin"
  | "computing_datainf"
  | "completed"
  | "failed";

export interface Job {
  id: string;
  status: JobStatus;
  status_message: string | null;
  progress: number;
  model_name: string;
  hyperparameters: Hyperparameters;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface Hyperparameters {
  learning_rate: number;
  epochs: number;
  batch_size: number;
  lora_rank: number;
  lora_alpha: number;
  lora_dropout: number;
  checkpoint_interval: number;
  max_seq_length: number;
  datainf_damping: number;
}

export const DEFAULT_HYPERPARAMETERS: Hyperparameters = {
  learning_rate: 2e-4,
  epochs: 3,
  batch_size: 4,
  lora_rank: 16,
  lora_alpha: 32,
  lora_dropout: 0.05,
  checkpoint_interval: 50,
  max_seq_length: 512,
  datainf_damping: 0.1,
};

export interface TrainingPair {
  prompt: string;
  completion: string;
  category: string;
}

export interface EvalExample {
  question: string;
  completion: string;
}

export interface CreateJobRequest {
  model_name: string;
  hyperparameters?: Partial<Hyperparameters>;
  training_pairs?: TrainingPair[];
  eval_examples: EvalExample[];
  dataset_file_path?: string;
}

export interface JobCreatedResponse {
  job_id: string;
  status: string;
}

export interface InfluenceScoreRow {
  train_id: string;
  eval_id: string;
  train_index: number;
  train_category: string;
  eval_index: number;
  train_prompt: string;
  eval_question: string;
  tracin_score: number;
  datainf_score: number;
}

export interface ScoresResponse {
  job_id: string;
  total: number;
  scores: InfluenceScoreRow[];
}

export interface UploadUrlResponse {
  upload_url: string;
  storage_path: string;
}

// ============================================================
// Frontend-only types
// ============================================================

export interface Dataset {
  id: string;
  name: string;
  examples: TrainingPair[];
  created_at: string;
}

export interface EvalSet {
  id: string;
  name: string;
  examples: EvalExample[];
  created_at: string;
}

// Heatmap matrix (derived client-side from scores)
export interface HeatmapData {
  categories: string[];
  evalQuestions: string[];
  matrix: number[][]; // [category_idx][eval_idx]
}

// Aggregated scores per category
export interface CategoryAggregate {
  category: string;
  tracin_total: number;
  datainf_total: number;
  eval_contributions: { eval_question: string; tracin: number; datainf: number }[];
}
