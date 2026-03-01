import type {
  CreateJobRequest,
  Job,
  JobCreatedResponse,
  ScoresResponse,
  UploadUrlResponse,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function apiFetch<T>(
  path: string,
  options: RequestInit & { token?: string } = {}
): Promise<T> {
  const { token, ...fetchOptions } = options;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(fetchOptions.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...fetchOptions,
    headers,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `API error: ${res.status}`);
  }

  return res.json();
}

// ============================================================
// Jobs
// ============================================================

export async function createJob(
  token: string,
  body: CreateJobRequest
): Promise<JobCreatedResponse> {
  return apiFetch("/api/v1/jobs", {
    method: "POST",
    body: JSON.stringify(body),
    token,
  });
}

export async function listJobs(
  token: string,
  status?: string
): Promise<Job[]> {
  const params = status ? `?status=${status}` : "";
  return apiFetch(`/api/v1/jobs${params}`, { token });
}

export async function getJob(token: string, jobId: string): Promise<Job> {
  return apiFetch(`/api/v1/jobs/${jobId}`, { token });
}

export async function getScores(
  token: string,
  jobId: string,
  params?: {
    category?: string;
    sort_by?: string;
    order?: string;
    limit?: number;
    offset?: number;
  }
): Promise<ScoresResponse> {
  const searchParams = new URLSearchParams();
  if (params) {
    Object.entries(params).forEach(([key, val]) => {
      if (val !== undefined) searchParams.set(key, String(val));
    });
  }
  const qs = searchParams.toString();
  return apiFetch(`/api/v1/jobs/${jobId}/scores${qs ? `?${qs}` : ""}`, {
    token,
  });
}

export async function deleteJob(
  token: string,
  jobId: string
): Promise<{ message: string }> {
  return apiFetch(`/api/v1/jobs/${jobId}`, { method: "DELETE", token });
}

// ============================================================
// Datasets
// ============================================================

export async function getUploadUrl(
  token: string,
  filename: string
): Promise<UploadUrlResponse> {
  return apiFetch(`/api/v1/datasets/upload-url?filename=${encodeURIComponent(filename)}`, {
    method: "POST",
    token,
  });
}
