# IssuePilot

IssuePilot scouts GitHub overnight and leaves a ranked, locally prepared issue queue for
the morning. For every selected issue it shallow-clones the repository, detects its
toolchain and architecture, and writes a focused context bundle. The dashboard then starts
an interactive Codex session in that repository with the prepared prompt.

No OpenAI API is used. Codex handoff uses the locally installed Codex CLI and the user's
existing Codex authentication.

## What works in this MVP

- GitHub issue search through PyGithub, with repository eligibility filters.
- A transparent 0–100 ranking based on stars, commit recency, maintainer activity, tests,
  CI, issue age, and comment count.
- Shallow clone/update through GitPython.
- Local analysis of language, framework, package manager, formatting, linting, tests, CI,
  important directories, commands, and a lightweight NetworkX architecture graph.
- The complete seven-file `tasks/issueNNN/` bundle requested by the project.
- SQLite persistence through SQLAlchemy.
- A FastAPI API and a responsive React/TypeScript/Tailwind dashboard.
- Real Solve, Favorite, Skip, and Archive behavior.
- A local Codex CLI launch with the workspace and prompt already loaded.

## Requirements

- Python 3.12
- Node.js 20 or newer (only needed to build the dashboard)
- Git
- A GitHub token is strongly recommended
- Optional: [Codex CLI](https://developers.openai.com/codex/cli/) for one-click Solve

## Install

```powershell
git clone <your-issuepilot-repository>
cd IssuePilot
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Create a classic GitHub personal access token with public repository read access and put it
in `.env`:

```dotenv
GITHUB_TOKEN=github_pat_...
```

Without a token GitHub permits only a small unauthenticated request budget, which is often
not enough for repository inspection.

Build the dashboard once:

```powershell
cd frontend
npm install
npm run build
cd ..
```

## Use it tomorrow morning

Run the overnight preparation:

```powershell
issuepilot overnight
```

Then open the dashboard:

```powershell
issuepilot dashboard
```

`dashboard` starts the local server and opens <http://127.0.0.1:8000>. You may instead run
`issuepilot serve` if you do not want a browser opened automatically.

### Schedule overnight on Windows

After confirming the command works in your activated environment, create a Task Scheduler
task that runs daily. Use the virtual environment's executable directly:

```text
Program: C:\path\to\IssuePilot\.venv\Scripts\issuepilot.exe
Arguments: overnight
Start in: C:\path\to\IssuePilot
```

Enable “Run whether user is logged on or not” if desired. Logs go to the scheduler history
and standard output; redirect them in the task action if durable log files are required.

## Configuration

All runtime settings are read from `.env`.

| Variable | Default | Purpose |
|---|---:|---|
| `GITHUB_TOKEN` | empty | GitHub authentication and higher rate limit |
| `ISSUEPILOT_DATABASE_URL` | `sqlite:///./data/issuepilot.db` | SQLAlchemy database URL |
| `ISSUEPILOT_WORKSPACE` | `./workspaces` | cloned repositories |
| `ISSUEPILOT_TASKS_DIR` | `./tasks` | generated context bundles |
| `ISSUEPILOT_MAX_ISSUES` | `10` | repositories prepared per run |
| `ISSUEPILOT_MIN_STARS` | `100` | minimum repository stars |
| `ISSUEPILOT_MAX_REPO_SIZE_KB` | `500000` | avoid unexpectedly large clones |
| `ISSUEPILOT_GITHUB_QUERY` | good-first-issue query | GitHub issue search syntax |
| `ISSUEPILOT_LOG_LEVEL` | `INFO` | Python log level |
| `ISSUEPILOT_FRONTEND_URL` | `http://localhost:5173` | development CORS origin |
| `ISSUEPILOT_API_URL` | `http://127.0.0.1:8000` | dashboard URL |

Example custom query:

```dotenv
ISSUEPILOT_GITHUB_QUERY=is:issue is:open label:"help wanted" language:python archived:false
```

## Codex handoff

Solve detects `codex` on `PATH`. When available it starts the stable interactive CLI with:

- the selected repository as the working directory;
- `workspace-write` sandbox permissions;
- the generated `.issuepilot-prompt.md` as the initial prompt.

That is a genuine automatic start; it does not call a paid LLM API from IssuePilot. Codex
itself may require the user to be logged in and entitled to use it.

If `codex` is absent, IssuePilot opens the prepared repository and creates
`Start IssuePilot Codex.cmd` (Windows) or `start-issuepilot-codex.sh` (macOS/Linux). This is
truthfully reported in the dashboard. After Codex CLI is installed and authenticated, that
file is the remaining manual start action.

## Context bundles

Each prepared issue gets:

```text
tasks/
└── issue001/
    ├── issue.md
    ├── context.md
    ├── repository_summary.md
    ├── architecture.md
    ├── commands.md
    ├── relevant_files.md
    └── priority.json
```

Detection is deliberately conservative. If a reliable test or lint command cannot be
derived from project metadata, the bundle says so instead of inventing one.

## Development

Backend:

```powershell
ruff check .
ruff format --check .
pytest
issuepilot serve --reload
```

Dashboard:

```powershell
cd frontend
npm run dev
npm run lint
npm run build
```

The development server proxies `/api` to FastAPI on port 8000.

## Architecture

`domain.py` contains framework-independent candidate and ranking values.
`services/` owns GitHub discovery, deterministic ranking, Git operations, analysis, bundle
generation, orchestration, and Codex launch. `models.py` and `db.py` are the persistence
boundary, while `api.py` and `cli.py` are thin delivery layers.

Future post-Codex behavior is defined as typed protocols in `workflows/contracts.py`:
validation, test execution, PR publishing, and an approval gate. They are intentionally not
shown as dashboard actions because no implementation exists yet. A future implementation
must put the approval gate before any remote write or PR publication.

## Known MVP limitations

- GitHub's search result quality and rate limits depend on the configured token and query.
- Repository analysis is static heuristic detection; it does not execute untrusted project
  code during the overnight scan.
- Estimated difficulty, duration, and acceptance probability are transparent heuristics,
  not ML predictions.
- IssuePilot launches Codex but does not currently observe session completion. Therefore
  validation and PR workflows remain contracts only, with no pretend controls.
- Clone updates reset IssuePilot's disposable shallow clone to the fetched remote branch.
  Do not use `workspaces/` for unrelated personal changes.
- Public repositories are the supported MVP target. Private repositories may work when both
  the GitHub token and local Git credentials have access, but are not separately managed.

## Security

IssuePilot never sends repository contents to an IssuePilot service and stores all state
locally. It does not execute cloned code during scanning. Codex is launched with
`workspace-write`, not unrestricted system access. Tokens belong only in `.env`, which is
gitignored.

