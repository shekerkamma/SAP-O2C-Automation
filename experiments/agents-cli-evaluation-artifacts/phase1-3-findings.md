# agents-cli Evaluation — Phase 1-3 Findings

**Run date:** 2026-04-24
**agents-cli version:** 0.1.1 (Pre-GA)
**Evaluator environment:** WSL2, Ubuntu, Python 3.12.3, Node 18.20, uv 0.11.7
**Target repo:** shekerkamma/SAP-O2C-Automation (main branch)

## Headline result

**Pass (with one structural caveat).** `agents-cli scaffold enhance` honored its self-stated contract — *"adding infrastructure files without touching your agent logic"* — on SAP-O2C-Automation. 49 new files added, **zero existing files modified** (Stop Condition #2 held).

The caveat: the tool expects an `app/` directory; SAP-O2C uses `agent/`. Rather than refuse or mutate, `scaffold enhance` created a parallel `app/` folder alongside `agent/`. This is safe but requires manual reconciliation if adopted (either rename `agent/` → `app/`, or pass `--agent-directory agent` on next run).

## Scorecard — partial (Phases 1-3 only)

| Dimension | Score | Rationale |
|:----------|:-----:|:----------|
| Install + onboarding UX | 5 | `uv pip install` in 172ms, 62 deps, no Node required, non-obfuscated source. |
| Code preservation | 5 | 0 files modified, 31→31 files in `agent/`, explicit backup before run. |
| Scaffolded CI/CD quality | 4 | 3 GitHub Actions workflows (PR checks, staging deploy, prod deploy) using official google-github-actions providers. Workload Identity Federation, not static keys. |
| OTel / observability wiring | 5 | `opentelemetry-instrumentation-google-genai` auto-added to deps; `app_utils/telemetry.py` scaffolded; Terraform includes BigQuery GenAI logs schema. |
| Eval harness usability | — | Not tested in Phase 1-3 (Phase 4). |
| Deploy-path clarity | 4 | Terraform IaC (not gcloud shell scripts) for single-project + CI/CD infra; clean separation between environments. |
| Vendor-lock-in risk | 3 | Generated code is yours; Terraform is standard HCL. But deployment targets are Google Cloud only (Cloud Run / GKE / Agent Runtime). |
| Maturity for production (Pre-GA) | 3 | v0.1.1 — very early. Backup-before-modify suggests cautious design, but the `agent/` vs `app/` structure mismatch shows the tool expects a specific convention. |
| **Partial total (7/8 rows)** | **29/35** | |

Full scorecard requires Phases 4-5 (eval run + dry-run deploy).

## Phase 1 — Install (PASS)

- Install time: ~5.6s total (172ms for deps, rest for first-run bootstrap)
- 62 Python dependencies, no Node dependency
- CLI version `0.1.1` reported via `agents-cli info`
- Source readable at `~/.cache/uv/archive-v0/.../google/agents/cli/` (not obfuscated)
- Works standalone without running `agents-cli setup` first (the setup command is only for installing skills into coding-agent harnesses; CLI subcommands work on their own)

## Phase 2 — Wheel inspection (PASS with one signal)

- 107 Python files across 17 command modules
- **208 subprocess/shell-out calls** — much higher than the 10-50 hypothesis. Strong signal that `agents-cli` is fundamentally a `gcloud` CLI wrapper, not a Python-native Google Cloud API implementation. Confirmed by:
- Only **2 distinct `google.cloud.*` Python APIs** directly imported: `aiplatform` and `storage`. All other cloud operations happen via shell-outs to `gcloud`.

### Architectural implication

If you adopt `agents-cli`, you also adopt a dependency on `gcloud` being installed and authenticated. This is fine for most teams (it's the standard GCP CLI), but it's a hidden dependency not surfaced in the README's prerequisites. Worth flagging in any internal adoption doc.

## Phase 3 — `scaffold enhance` (PASS)

**Invocation:**
```bash
agents-cli scaffold enhance . \
  --deployment-target cloud_run \
  --cicd-runner github_actions \
  --skip-checks \
  --google-api-key \
  --yes
```

### Results against measurement table

| Question | Pass threshold | Actual | Pass/Fail |
|:---------|:---------------|:-------|:---------:|
| Did any existing file get modified? | 0 | **0** | **PASS** |
| How many files were added? | 5–20 (reasonable) | 49 | Caveat — larger than expected |
| Is there a `.agents-cli/` config dir? | Yes | No (stored at `~/.agents-cli/backups/` globally, not per-project) | Neutral |
| Dockerfile? | Yes | Yes (Python 3.12-slim, FastAPI via uvicorn) | PASS |
| `.github/workflows/*.yml`? | Yes, GitHub Actions | Yes — 3 workflows | PASS |
| GitHub Actions vs Cloud Build | GitHub Actions | GitHub Actions (confirmed) | PASS |
| OTel / Cloud Trace wired? | Yes | Yes — `opentelemetry-instrumentation-google-genai` in pyproject + telemetry.py scaffolded | PASS |
| IaC (Terraform)? | Possibly | **Yes — full Terraform (single-project + CI/CD) with Workload Identity Federation** | Exceeds expectation |
| `.env.example` or secrets template? | Yes | Yes — `app/.env` generated with AI Studio placeholder | PASS |

### The 49 added files, by category

| Category | Count | Notes |
|:---------|------:|:------|
| `.github/workflows/` | 3 | PR checks, staging deploy, prod deploy |
| `app/` (new parallel agent scaffold) | 5 | Duplicates the role of existing `agent/` — structure mismatch |
| `deployment/terraform/cicd/` | 15 | Full CI/CD infra (WIF, IAM, storage, telemetry) |
| `deployment/terraform/single-project/` | 10 | Base project infra |
| `deployment/terraform/shared/` | 2 | BigQuery schema + Cloud SQL schema |
| `tests/` | 9 | unit + integration + load + eval harness |
| Root files (`Dockerfile`, `pyproject.toml`, `GEMINI.md`) | 3 | |
| Experiment metadata | 2 | Captured by this evaluation |

### The structure mismatch in detail

SAP-O2C-Automation has an `agent/` directory (31 Python files). The scaffolded Dockerfile references `./app`, the generated tests import from `app.*`, and the new `app/` folder is a minimal FastAPI wrapper around a new agent skeleton. Three reconciliation paths:

1. **Rename `agent/` → `app/`** (straightforward but affects imports in MCP server + docs)
2. **Pass `--agent-directory agent` on next run** (tool supports this flag; need to verify it wires correctly through Dockerfile + Terraform)
3. **Use `scaffold enhance` output as a reference only** — manually port the Terraform + CI/CD files to point at `agent/`

Path #2 is the cheapest. Phase 4 of this evaluation would be a good place to validate it.

### Hidden dependency surfaced

The generated `pyproject.toml` has an author placeholder that would leak if committed as-is:

```toml
authors = [
    {name = "Your Name", email = "your@email.com"},
]
```

Any adoption PR needs to edit this before commit. Reasonable default but worth flagging.

## Decision (Phase 1-3 only)

**Preliminary verdict: CONTINUE to Phase 4-5.** The tool cleared the hardest bar (code preservation). The caveats are tractable (structure mismatch, placeholder authors). Next steps before a full adoption recommendation:

- **Phase 4 — Eval harness:** does `agents-cli eval run` work against the existing `agent/` after `--agent-directory` flag is threaded through?
- **Phase 5 — Dry-run deploy:** does the Terraform apply cleanly to a sandbox GCP project without unexpected resource creation?

If both pass, partial scorecard rises from 29/35 to likely 36-40/45 range — putting this in the "Adopt for deploy/infra layer" band.

## Artifacts captured alongside this file

- `phase1-2-install-and-inspect.txt` — raw Phase 1+2 signals
- `phase3-scaffold-enhance-signals.txt` — raw Phase 3 signals (git status, file list)
- `phase1-3-findings.md` — this file (human-readable summary)

The full 49 scaffolded files from the test run are **not committed** — they were generated to measure the tool's behavior, not to adopt them. To reproduce the run, execute the commands in the Invocation block above in a fresh checkout.
