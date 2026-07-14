export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type Run = {
  id: string;
  task_id: string;
  benchmark_run_id: string | null;
  status: string;
  model: string;
  prompt_key: string | null;
  runtime_key: string;
  final_output: unknown;
  score: string | null;
  passed: boolean | null;
  failure_type: string | null;
  total_steps: number;
  total_latency_ms: number;
  total_tokens: number;
  total_cost_usd: string;
  error: string | null;
  input: unknown;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
};

export type Step = {
  id: string;
  step_index: number;
  phase: string | null;
  thought: string | null;
  tool_name: string | null;
  tool_input: unknown;
  tool_output: unknown;
  observation: string | null;
  error: string | null;
  latency_ms: number | null;
  tokens: number;
  cost_usd: string;
  created_at: string;
};

export type Task = {
  id: string;
  task_key: string;
  name: string;
  description: string | null;
  spec: Record<string, unknown>;
};

export type TaskSet = {
  id: string;
  task_set_key: string;
  name: string;
  description: string | null;
  tasks: Task[];
};

export type BenchmarkRun = {
  id: string;
  task_set_id: string;
  status: string;
  config: Record<string, unknown>;
  summary: Record<string, unknown> | null;
  planned_runs: number;
  completed_runs: number;
  failed_runs: number;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
};

export type BenchmarkItem = {
  id: string;
  benchmark_run_id: string;
  run_id: string;
  task_id: string;
  model: string;
  prompt_key: string;
  runtime_key: string;
  repeat_index: number;
};

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `API request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function formatPercent(value: unknown) {
  return typeof value === "number" ? `${Math.round(value * 100)}%` : "-";
}

export function formatNumber(value: unknown, digits = 2) {
  return typeof value === "number" ? value.toFixed(digits) : "-";
}
