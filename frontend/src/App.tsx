import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Archive,
  CheckCircle2,
  Clock3,
  ExternalLink,
  Github,
  Heart,
  LoaderCircle,
  Play,
  RefreshCw,
  SkipForward,
  Star,
  TerminalSquare,
} from "lucide-react";
import { api, type Health, type Issue, type IssueStatus, type SolveResult } from "./api";

function formatDuration(minutes: number): string {
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  return remainder ? `${hours}h ${remainder}m` : `${hours}h`;
}

function App() {
  const [issues, setIssues] = useState<Issue[]>([]);
  const [health, setHealth] = useState<Health | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<SolveResult | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [nextIssues, nextHealth] = await Promise.all([api.issues(), api.health()]);
      setIssues(nextIssues);
      setHealth(nextHealth);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not load IssuePilot.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const stats = useMemo(
    () => ({
      ready: issues.filter((issue) => issue.status === "ready").length,
      favorites: issues.filter((issue) => issue.status === "favorite").length,
      average: issues.length
        ? Math.round(issues.reduce((sum, issue) => sum + issue.score, 0) / issues.length)
        : 0,
    }),
    [issues],
  );

  async function changeStatus(id: number, status: Exclude<IssueStatus, "solving">) {
    setBusy(id);
    setError(null);
    try {
      const updated = await api.status(id, status);
      if (status === "skipped" || status === "archived") {
        setIssues((current) => current.filter((issue) => issue.id !== id));
      } else {
        setIssues((current) => current.map((issue) => (issue.id === id ? updated : issue)));
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Action failed.");
    } finally {
      setBusy(null);
    }
  }

  async function solve(issue: Issue) {
    setBusy(issue.id);
    setError(null);
    setNotice(null);
    try {
      const result = await api.solve(issue.id);
      setNotice(result);
      if (result.launched) {
        setIssues((current) =>
          current.map((item) =>
            item.id === issue.id ? { ...item, status: "solving" } : item,
          ),
        );
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not start Codex.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200/80 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-5 lg:px-8">
          <div className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-xl bg-ink text-white">
              <Github size={21} aria-hidden />
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-tight">IssuePilot</h1>
              <p className="text-sm text-slate-500">Your overnight issue shortlist</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div
              className={`hidden items-center gap-2 rounded-full px-3 py-1.5 text-xs font-semibold sm:flex ${
                health?.codex_available
                  ? "bg-emerald-50 text-emerald-700"
                  : "bg-amber-50 text-amber-700"
              }`}
            >
              <span className="h-2 w-2 rounded-full bg-current" />
              {health?.codex_available ? "Codex ready" : "Codex CLI not detected"}
            </div>
            <button
              className="rounded-lg border border-slate-200 bg-white p-2.5 text-slate-600 hover:bg-slate-50"
              onClick={() => void load()}
              aria-label="Refresh issues"
            >
              <RefreshCw size={18} className={loading ? "animate-spin" : ""} />
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-5 py-8 lg:px-8">
        <section className="mb-8">
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-accent">Morning brief</p>
          <div className="mt-2 flex flex-col justify-between gap-5 sm:flex-row sm:items-end">
            <div>
              <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">Good issues, ready to solve.</h2>
              <p className="mt-2 max-w-2xl text-slate-600">
                Repositories are cloned, analyzed, and bundled with focused context for Codex.
              </p>
            </div>
            <div className="flex gap-6 text-sm">
              <Stat label="Ready" value={stats.ready} />
              <Stat label="Favorites" value={stats.favorites} />
              <Stat label="Avg score" value={stats.average} />
            </div>
          </div>
        </section>

        {error && (
          <div role="alert" className="mb-5 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
            {error}
          </div>
        )}
        {notice && (
          <div className={`mb-5 rounded-xl border px-4 py-3 text-sm ${
            notice.launched
              ? "border-emerald-200 bg-emerald-50 text-emerald-800"
              : "border-amber-200 bg-amber-50 text-amber-900"
          }`}>
            <div className="flex items-start gap-2">
              {notice.launched ? <CheckCircle2 size={18} /> : <TerminalSquare size={18} />}
              <span>{notice.message}</span>
            </div>
          </div>
        )}

        {loading ? (
          <div className="grid min-h-72 place-items-center text-slate-500">
            <LoaderCircle className="animate-spin" size={30} aria-label="Loading issues" />
          </div>
        ) : issues.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-12 text-center">
            <h3 className="text-lg font-semibold">No prepared issues yet</h3>
            <p className="mt-2 text-sm text-slate-500">
              Run <code className="rounded bg-slate-100 px-1.5 py-1">issuepilot overnight</code>,
              then refresh this page.
            </p>
          </div>
        ) : (
          <div className="grid gap-4">
            {issues.map((issue) => (
              <IssueCard
                key={issue.id}
                issue={issue}
                busy={busy === issue.id}
                onSolve={() => void solve(issue)}
                onStatus={(status) => void changeStatus(issue.id, status)}
              />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="text-xl font-bold">{value}</div>
      <div className="text-slate-500">{label}</div>
    </div>
  );
}

function IssueCard({
  issue,
  busy,
  onSolve,
  onStatus,
}: {
  issue: Issue;
  busy: boolean;
  onSolve: () => void;
  onStatus: (status: "favorite" | "ready" | "skipped" | "archived") => void;
}) {
  return (
    <article className="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-card sm:p-6">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-center">
        <div className="flex min-w-0 flex-1 gap-4">
          <div className="grid h-14 w-14 shrink-0 place-items-center rounded-xl bg-emerald-50">
            <div className="text-center">
              <div className="text-xl font-extrabold text-accent">{Math.round(issue.score)}</div>
              <div className="text-[9px] font-bold uppercase tracking-wide text-emerald-700">score</div>
            </div>
          </div>
          <div className="min-w-0">
            <a
              href={issue.repository_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 text-sm font-semibold text-accent hover:underline"
            >
              {issue.repository} <ExternalLink size={12} />
            </a>
            <h3 className="mt-1 text-lg font-bold leading-snug">
              <a href={issue.issue_url} target="_blank" rel="noreferrer" className="hover:underline">
                {issue.title}
              </a>
            </h3>
            <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs font-medium text-slate-500">
              <span className="flex items-center gap-1"><Star size={14} />{issue.stars.toLocaleString()}</span>
              <span className="flex items-center gap-1"><Clock3 size={14} />{formatDuration(issue.estimated_minutes)}</span>
              <span className={`rounded-full px-2.5 py-1 ${
                issue.difficulty === "easy"
                  ? "bg-emerald-50 text-emerald-700"
                  : issue.difficulty === "hard"
                    ? "bg-rose-50 text-rose-700"
                    : "bg-amber-50 text-amber-700"
              }`}>{issue.difficulty}</span>
              <span>{Math.round(issue.acceptance_probability * 100)}% acceptance estimate</span>
              {issue.has_tests && <span>Tests</span>}
              {issue.has_ci && <span>CI</span>}
            </div>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2 lg:justify-end">
          <button
            disabled={busy}
            onClick={onSolve}
            className="inline-flex items-center gap-2 rounded-lg bg-accent px-4 py-2.5 text-sm font-bold text-white hover:bg-emerald-800 disabled:opacity-50"
          >
            {busy ? <LoaderCircle size={16} className="animate-spin" /> : <Play size={16} fill="currentColor" />}
            Solve
          </button>
          <ActionButton
            label={issue.status === "favorite" ? "Unfavorite" : "Favorite"}
            icon={<Heart size={16} fill={issue.status === "favorite" ? "currentColor" : "none"} />}
            disabled={busy}
            onClick={() => onStatus(issue.status === "favorite" ? "ready" : "favorite")}
          />
          <ActionButton label="Skip" icon={<SkipForward size={16} />} disabled={busy} onClick={() => onStatus("skipped")} />
          <ActionButton label="Archive" icon={<Archive size={16} />} disabled={busy} onClick={() => onStatus("archived")} />
        </div>
      </div>
    </article>
  );
}

function ActionButton({
  label,
  icon,
  disabled,
  onClick,
}: {
  label: string;
  icon: React.ReactNode;
  disabled: boolean;
  onClick: () => void;
}) {
  return (
    <button
      aria-label={label}
      title={label}
      disabled={disabled}
      onClick={onClick}
      className="rounded-lg border border-slate-200 bg-white p-2.5 text-slate-600 hover:bg-slate-50 hover:text-ink disabled:opacity-50"
    >
      {icon}
    </button>
  );
}

export default App;
