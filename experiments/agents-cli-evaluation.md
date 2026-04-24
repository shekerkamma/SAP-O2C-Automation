# agents-cli Evaluation — SAP-O2C-Automation

**Experiment owner:** _____________________
**Date started:** _____________________
**Time budget:** 3–4 hours (one afternoon)
**agents-cli version under test:** _____________________  (fill in from `agents-cli info`)
**Maturity tier at time of test:** Pre-GA ("Preview")

## Purpose

Determine whether `agents-cli` (Google, Pre-GA) can usefully augment the existing SAP-O2C-Automation ADK project — specifically the *deploy + CI/CD + observability* layer that is currently hand-rolled. This is not a full rewrite evaluation; it's a narrow test of the `scaffold enhance` mode against our existing `agent/` directory.

**Decision this experiment informs:** Should we adopt `agents-cli scaffold enhance` for our deploy/infra path, wait for GA, or stay on our hand-rolled setup?

## Prerequisites (15 min)

Verify each one *before* starting — a failed prerequisite wastes the whole afternoon.

| Requirement | Check command | Must be |
|:------------|:--------------|:--------|
| Python 3.11+ | `python3 --version` | ≥ 3.11 |
| `uv` installed | `uv --version` | Any recent version |
| Node.js | `node --version` | ≥ 18 |
| Clean git working tree | `git status --porcelain` | Empty output |
| AI Studio API key available | `echo $GOOGLE_API_KEY` | Non-empty (local eval) |
| Google Cloud project | `gcloud config get-value project` | Non-empty OR skip deploy phase |
| Existing agent runs locally | `cd agent && adk web` | Works, responds to a test prompt |

**If any row fails: fix it before proceeding, or skip the phases that depend on it.**

## Baseline snapshot (15 min)

Capture what the repo looks like *before* agents-cli touches it. This is the control group.

```bash
# Create experiment branch
git checkout -b experiment/agents-cli-evaluation
mkdir -p experiments/agents-cli-evaluation-artifacts

# Baseline: file tree
find agent/ mcp-server/ -type f \
  ! -path '*/node_modules/*' ! -path '*/__pycache__/*' \
  | sort > experiments/agents-cli-evaluation-artifacts/baseline-tree.txt

# Baseline: LoC per file
find agent/ -type f -name '*.py' -exec wc -l {} + \
  > experiments/agents-cli-evaluation-artifacts/baseline-loc.txt

# Baseline: current CI config (if any)
ls -la .github/workflows/ 2>/dev/null \
  > experiments/agents-cli-evaluation-artifacts/baseline-ci.txt || \
  echo "No existing CI" > experiments/agents-cli-evaluation-artifacts/baseline-ci.txt

# Baseline: time a local agent run with a known prompt
time (cd agent && echo "Show me product P001 details" | adk run) \
  2> experiments/agents-cli-evaluation-artifacts/baseline-run-timing.txt
```

Record one-line summaries in the table below:

| Metric | Baseline value |
|:-------|:---------------|
| Total Python files in `agent/` | |
| Total LoC in `agent/` | |
| Existing CI workflows | |
| Time to first agent response (cold) | |
| Existing eval harness present? | |
| Existing OTel instrumentation? | |
| Existing Dockerfile? | |
| Existing deploy script? | |

## Phase 1 — Install (10 min)

```bash
# Install CLI + skills into the coding agent
uvx google-agents-cli setup

# Verify install
agents-cli info
agents-cli info > experiments/agents-cli-evaluation-artifacts/install-info.txt

# Check that skills were actually installed into your coding-agent harness
# (paths vary — check both)
ls ~/.claude/skills/ 2>/dev/null | grep -i agents
ls ~/.gemini/skills/ 2>/dev/null | grep -i agents
```

### Measurement — Install

| Question | Hypothesis | Actual | Pass/Fail |
|:---------|:-----------|:-------|:---------:|
| Did `uvx` complete without network errors? | Yes | | |
| Was a coding-agent harness auto-detected? | Yes (Claude Code or Gemini CLI) | | |
| Were skills installed to the detected harness? | Yes (7 skills) | | |
| Did `agents-cli info` print a valid version? | Yes | | |
| Install time (stopwatch) | < 60 seconds | _____ s | |

**Stop condition #1:** if install fails (auth errors, registry errors, incompatible Python version) — document the failure in `install-info.txt`, skip to the Synthesis section.

## Phase 2 — Inspect what was installed (20 min)

Open the installed CLI wheel and read what it's actually doing. This is a one-time audit and matters because the CLI is closed-source — you only get this visibility by extracting the wheel.

```bash
# Find the installed wheel
uv pip show google-agents-cli | grep Location
# Then: find that dir's .dist-info, or reinstall to a known path:
uv pip install --target /tmp/agents-cli-audit google-agents-cli
ls /tmp/agents-cli-audit/

# Read the entry points
cat /tmp/agents-cli-audit/google_agents_cli/__main__.py 2>/dev/null | head -40

# Check what it shells out to
grep -rn 'subprocess\|shell=True' /tmp/agents-cli-audit/ | \
  head -30 > experiments/agents-cli-evaluation-artifacts/shell-outs.txt

# Check what Google Cloud APIs it touches
grep -rn 'google.cloud\|googleapiclient' /tmp/agents-cli-audit/ | \
  cut -d: -f1 | sort -u > experiments/agents-cli-evaluation-artifacts/gcp-apis-touched.txt
```

### Measurement — Inspection

| Question | Hypothesis | Actual |
|:---------|:-----------|:-------|
| Wheel extracts cleanly (no obfuscation)? | Yes | |
| Shell-out count (subprocess calls) | 10–50 | |
| Distinct Google Cloud APIs touched | 5–15 | |
| Any calls to external (non-Google) services? | No | |
| Telemetry/phone-home detected? | Unclear — check for `requests.post` to google.* | |

**Note anything surprising** in `experiments/agents-cli-evaluation-artifacts/inspection-notes.md`. In particular, any telemetry calls that aren't documented in the README.

## Phase 3 — Run `scaffold enhance` on the existing agent (30 min)

This is the core test. Does `enhance` add things alongside your code, or does it mutate your code?

```bash
# Capture pre-state for precise diff
git add -A && git commit -m "wip: pre-enhance snapshot" || true

# Run enhance in the agent directory
cd agent/
agents-cli scaffold enhance 2>&1 | \
  tee ../experiments/agents-cli-evaluation-artifacts/enhance-stdout.txt

cd ..

# Observe the damage (or lack of it)
git status > experiments/agents-cli-evaluation-artifacts/enhance-git-status.txt
git diff --stat > experiments/agents-cli-evaluation-artifacts/enhance-diff-stat.txt
git diff > experiments/agents-cli-evaluation-artifacts/enhance-full-diff.patch

# Classify the changes
{
  echo "=== Added files ==="
  git status --porcelain | grep '^??' | awk '{print $2}'
  echo ""
  echo "=== Modified files ==="
  git status --porcelain | grep '^.M' | awk '{print $2}'
  echo ""
  echo "=== Deleted files ==="
  git status --porcelain | grep '^.D' | awk '{print $2}'
} > experiments/agents-cli-evaluation-artifacts/enhance-change-classification.txt
```

### Measurement — Enhance

| Question | Pass threshold | Actual | Pass/Fail |
|:---------|:---------------|:-------|:---------:|
| Did any existing file in `agent/` get modified? | **Zero existing files modified** | | |
| How many files were added? | 5–20 (reasonable) | | |
| Is there a `.agents-cli/` config dir? | Yes | | |
| Is there a `Dockerfile` or equivalent? | Yes | | |
| Is there a `.github/workflows/*.yml`? | Yes, GitHub Actions | | |
| Does the CI assume GitHub Actions or Cloud Build? | GitHub Actions | | |
| Does it wire OTel/Cloud Trace? | Yes (look for `opentelemetry` imports in new files) | | |
| Does it add IaC (Terraform, etc.)? | Possibly | | |
| Is there a `.env.example` or secrets template? | Yes | | |

**Stop condition #2:** if `scaffold enhance` modifies *any* existing file in `agent/` (as opposed to only adding new files) — stop, document in `enhance-full-diff.patch`, consult team before continuing. Mutation of existing code is a trust-breaker for automated scaffolding.

### Manual read-through (15 min of the 30)

Read the newly-added files. Look for:

- [ ] **Hardcoded assumptions** about Cloud Run vs GKE vs Agent Runtime — does the scaffold commit you to one?
- [ ] **Hardcoded project IDs** or region names that would leak to git
- [ ] **Authentication mechanism** — is it Workload Identity, service account keys, or user-OAuth?
- [ ] **Cost implications** — does the infra config default to "always-on" or "scale-to-zero"?
- [ ] **CI workflow triggers** — does it try to deploy on every push to main? (Usually wrong default for an experimental repo.)

Write one-line findings into `experiments/agents-cli-evaluation-artifacts/enhance-readthrough-notes.md`.

## Phase 4 — Run `eval run` against existing agent (30 min)

Can the eval harness consume your existing agent without modification?

```bash
# First check: does it detect your existing agent config?
agents-cli eval run --help 2>&1 | \
  tee experiments/agents-cli-evaluation-artifacts/eval-help.txt

# Dry run with a trivial evalset (if one exists in the scaffold)
agents-cli eval run 2>&1 | \
  tee experiments/agents-cli-evaluation-artifacts/eval-firstrun.txt
```

### Measurement — Eval

| Question | Hypothesis | Actual | Pass/Fail |
|:---------|:-----------|:-------|:---------:|
| Does `eval run` auto-discover your existing agent? | Yes (uses `.agents-cli/` config) | | |
| Does it require an evalset file, or bundle defaults? | Requires evalset | | |
| Does local eval work with AI Studio API key only (no GCP)? | Yes | | |
| Time to run a 5-case evalset | 30–120 seconds | | |
| Does it produce a comparable output format to your existing tests? | Unlikely (new format) | | |

**Stop condition #3:** if `eval run` requires Google Cloud authentication for *local* evaluations (despite README saying AI Studio API key is enough), document that as a major gap and skip the deploy phase — you're beyond free-tier territory and the afternoon budget won't cover auth setup.

### Build a small evalset from existing tests

If your current repo has tests for the agent, convert 3-5 cases to agents-cli's evalset format:

```bash
# Find existing test cases
find . -name 'test_*.py' -o -name '*_test.py' | head -5

# Then: manually write 3-5 cases as an evalset YAML/JSON
# (format TBD from agents-cli docs — check .agents-cli/evalsets/ for examples)
```

Record in `experiments/agents-cli-evaluation-artifacts/eval-comparison.md`:

| Test case | Existing setup pass? | agents-cli eval pass? | Notes |
|:----------|:--------------------:|:---------------------:|:------|
| Product lookup happy path | | | |
| Product lookup not found | | | |
| Sales order status query | | | |
| Multi-turn refinement | | | |
| Cross-entity (inventory + sales) | | | |

**Any row where the two columns diverge is a concrete finding** worth discussing.

## Phase 5 — Dry-run deploy (20 min)

**Do not actually deploy.** The `--dry-run` flag (if supported) or a separate sandbox project is mandatory.

```bash
# Check whether dry-run is supported
agents-cli deploy --help 2>&1 | grep -i dry

# If --dry-run exists
agents-cli deploy --target cloud-run --dry-run 2>&1 | \
  tee experiments/agents-cli-evaluation-artifacts/deploy-dryrun.txt

# If no --dry-run flag — STOP. Do not run actual deploy in this experiment.
# Document as a finding: "deploy has no dry-run mode; cannot evaluate safely"
```

### Measurement — Deploy (dry-run)

| Question | Hypothesis | Actual |
|:---------|:-----------|:-------|
| Is there a `--dry-run` flag? | Yes | |
| Does the plan show only additive cloud resources? | Mostly | |
| Does it deploy into an existing VPC or create a new one? | Varies | |
| Is there a cost estimate? | Probably not (Google tools rarely include) | |
| Does it require any IAM permissions you don't have? | Check against list | |
| Estimated monthly cost (from resource list + GCP pricing) | | |

## Synthesis — Scorecard (30 min)

Close the experiment. Write the summary to `experiments/agents-cli-evaluation.md#results`.

### Scorecard

Score each dimension 1–5 (1 = worse than current, 3 = at parity, 5 = substantially better):

| Dimension | Score | Rationale |
|:----------|:-----:|:----------|
| Install + onboarding UX | | |
| Code preservation (did our existing code survive untouched?) | | |
| Scaffolded CI/CD quality | | |
| OTel / observability wiring | | |
| Eval harness usability | | |
| Deploy-path clarity | | |
| Vendor-lock-in risk | | |
| Maturity for production (Pre-GA reality check) | | |
| **Total (out of 40)** | | |

### Decision matrix

| Total score | Recommendation |
|:-----------:|:---------------|
| 32–40 | **Adopt** for the deploy/infra layer. Keep existing agent logic; delegate boilerplate. |
| 24–31 | **Wait for GA.** Useful direction, but Pre-GA risk + gaps are too much for production commitment. |
| 16–23 | **Monitor only.** Check again in 3 months. Not ready for our stack. |
| < 16 | **Pass.** Our hand-rolled setup is strictly better; re-evaluate only if a specific gap emerges. |

### Results (fill in at end of afternoon)

> **Overall verdict:** _________________________
>
> **Top 3 wins:**
> 1.
> 2.
> 3.
>
> **Top 3 gaps or concerns:**
> 1.
> 2.
> 3.
>
> **Surprises (what I didn't expect before running the experiment):**
> 1.
> 2.
>
> **Next action:** _________________________
>
> **Time spent:** _____ hours (vs 3–4 hour budget)

## Cleanup

```bash
# If you're not adopting yet: restore original state
git reset --hard HEAD
git checkout main
git branch -D experiment/agents-cli-evaluation

# Keep the artifacts — they're the deliverable
# (They live in experiments/agents-cli-evaluation-artifacts/, which is on main
# after merging this eval branch — OR keep them as loose local files.)

# Uninstall the CLI if not proceeding
uv pip uninstall google-agents-cli
```

## Sharing the result

This markdown file + the `experiments/agents-cli-evaluation-artifacts/` directory is the deliverable. Options:

- **Blog post / internal memo:** copy the "Results" section verbatim; it's written to be shared.
- **Team discussion:** walk through the scorecard row-by-row. Each row is a talking point with concrete evidence in the artifacts dir.
- **PR comment / decision log:** link to this file in a Linear/Jira ticket under the decision record for your agent platform roadmap.

## Assumptions & caveats

- This evaluation was performed against **Pre-GA** `agents-cli`. Behavior may change before GA.
- The evaluator's existing stack is: Python ADK + TypeScript MCP server + Codespaces-hosted free tier.
- Results are specific to one engineer's afternoon; production adoption requires broader signals (team consensus, cost modeling, security review).
- The `enhance` mode test does not cover the `scaffold <new>` (greenfield) path. A separate evaluation would be required to assess that.
