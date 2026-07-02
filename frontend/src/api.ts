export type IssueStatus = "ready" | "favorite" | "skipped" | "archived" | "solving";

export interface Issue {
  id: number;
  number: number;
  repository: string;
  repository_url: string;
  title: string;
  issue_url: string;
  labels: string[];
  stars: number;
  comments: number;
  score: number;
  difficulty: "easy" | "medium" | "hard";
  estimated_minutes: number;
  acceptance_probability: number;
  status: IssueStatus;
  has_tests: boolean;
  has_ci: boolean;
  bundle_path: string | null;
  repository_metadata: Record<string, unknown>;
  ranking_factors: Record<string, number>;
  issue_created_at: string;
  scanned_at: string;
}

export interface Health {
  status: string;
  database: string;
  codex_available: boolean;
}

export interface SolveResult {
  launched: boolean;
  method: string;
  message: string;
  workspace_path: string;
  prompt_path: string;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, options);
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<Health>("/api/health"),
  issues: () => request<Issue[]>("/api/issues"),
  status: (id: number, status: Exclude<IssueStatus, "solving">) =>
    request<Issue>(`/api/issues/${id}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    }),
  solve: (id: number) =>
    request<SolveResult>(`/api/issues/${id}/solve`, { method: "POST" }),
};

