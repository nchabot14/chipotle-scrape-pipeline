# Scheduled Firecrawl scrape workflow — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run `scrape_pipeline.py` daily on GitHub Actions, committing any new or changed files in `knowledge/raw/` back to `main`, with a manual-trigger button for ad-hoc runs.

**Architecture:** A single workflow file (`.github/workflows/scrape.yml`) on a `cron` + `workflow_dispatch` trigger. One job: checkout → setup Python → `pip install -r requirements.txt` → run the script with `API_KEY` mapped from a GitHub secret → `git add knowledge/raw && commit && push` (skip if no diff). Uses the default `GITHUB_TOKEN` with `contents: write`, which by design does not re-trigger workflows.

**Tech Stack:** GitHub Actions (`ubuntu-latest`), `actions/checkout@v4`, `actions/setup-python@v5` (Python 3.12, pip cache), git CLI, `requests`, `python-dotenv`.

**Spec:** `docs/superpowers/specs/2026-05-06-github-actions-scrape-schedule-design.md`

---

## File structure

| Path | Status | Responsibility |
| --- | --- | --- |
| `requirements.txt` | new | Runtime dependencies for CI installs |
| `.github/workflows/scrape.yml` | new | Daily scheduled + manual scrape, commit-back to `main` |
| `scrape_pipeline.py` | unchanged | Already reads `API_KEY` from env; `load_dotenv()` is a no-op in CI |
| `.gitignore` | unchanged | `knowledge/raw/` already tracked |

No tests file exists or will be added. Verification is operational: trigger the workflow with `workflow_dispatch` and inspect the run + resulting commit.

---

### Task 1: Add `requirements.txt`

**Files:**
- Create: `requirements.txt`

- [ ] **Step 1: Create `requirements.txt`**

Contents:

```
requests
python-dotenv
```

Versions intentionally unpinned (per spec "Out of scope" — pinning can come later).

- [ ] **Step 2: Verify the file installs cleanly in a fresh venv**

Run:

```bash
python3 -m venv /tmp/scrape-verify-venv
/tmp/scrape-verify-venv/bin/pip install -q -r requirements.txt
/tmp/scrape-verify-venv/bin/python -c "import requests, dotenv; print('ok')"
rm -rf /tmp/scrape-verify-venv
```

Expected output: `ok`

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "chore: pin scrape pipeline runtime deps in requirements.txt"
```

---

### Task 2: Add the workflow file

**Files:**
- Create: `.github/workflows/scrape.yml`

- [ ] **Step 1: Create `.github/workflows/scrape.yml`**

Contents (copy verbatim):

```yaml
name: Scheduled Firecrawl scrape

on:
  schedule:
    - cron: "0 13 * * *"   # 13:00 UTC daily (~8am Central in DST, 7am in standard time)
  workflow_dispatch:

permissions:
  contents: write

jobs:
  scrape:
    runs-on: ubuntu-latest
    steps:
      - name: Check out repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
          cache-dependency-path: requirements.txt

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run scraper
        env:
          API_KEY: ${{ secrets.FIRECRAWL_API_KEY }}
        run: python scrape_pipeline.py

      - name: Commit scraped files
        run: |
          git config user.name  "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add knowledge/raw
          if git diff --cached --quiet; then
            echo "No changes to commit"
            exit 0
          fi
          git commit -m "chore(scrape): update knowledge/raw ($(date -u +%Y-%m-%dT%H:%MZ))"
          git push
```

Notes for the implementer:

- The `41898282+github-actions[bot]@...` email is the canonical one for the `github-actions[bot]` user; do not change it.
- `cache-dependency-path: requirements.txt` makes `setup-python`'s pip cache invalidate when deps change.
- `permissions: contents: write` is required so the default `GITHUB_TOKEN` can `git push`.

- [ ] **Step 2: Lint the YAML locally**

Run:

```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/scrape.yml'))" && echo OK
```

Expected output: `OK`

- [ ] **Step 3: Sanity-check key fields**

Run:

```bash
grep -nE 'cron:|workflow_dispatch:|FIRECRAWL_API_KEY|contents: write|python scrape_pipeline\.py' .github/workflows/scrape.yml
```

Expected: each of the five patterns appears at least once.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/scrape.yml
git commit -m "ci: add daily Firecrawl scrape workflow with commit-back"
```

---

### Task 3: Push to GitHub

**Files:** none (git operation only)

- [ ] **Step 1: Push `main`**

Run:

```bash
git push origin main
```

Expected: push succeeds, two new commits visible on `origin/main`.

- [ ] **Step 2: Confirm the workflow appears in the Actions tab**

Open `https://github.com/nchabot14/chipotle-scrape-pipeline/actions` in a browser and confirm "Scheduled Firecrawl scrape" is listed in the left sidebar.

If it doesn't appear, re-check that the file path is exactly `.github/workflows/scrape.yml` (case-sensitive on GitHub's side) and that YAML parsing succeeded in Task 2.

---

### Task 4: Add the `FIRECRAWL_API_KEY` repository secret

**Files:** none (GitHub UI action)

This step has no CLI equivalent that doesn't require a separate auth token; do it in the browser.

- [ ] **Step 1: Read the local API key value**

Run:

```bash
grep -E '^API_KEY=' .env
```

Expected: a line of the form `API_KEY=fc-...`. Copy the value after the `=`.

- [ ] **Step 2: Add the secret in GitHub**

Navigate to:
`https://github.com/nchabot14/chipotle-scrape-pipeline/settings/secrets/actions`

Click **New repository secret**:

- Name: `FIRECRAWL_API_KEY`
- Secret: paste the value from Step 1.

Click **Add secret**.

- [ ] **Step 3: Confirm the secret is listed**

On the same page, confirm `FIRECRAWL_API_KEY` appears under "Repository secrets" with an "Updated now" timestamp.

---

### Task 5: Verify with a manual run

**Files:** none

- [ ] **Step 1: Trigger the workflow manually**

Navigate to:
`https://github.com/nchabot14/chipotle-scrape-pipeline/actions/workflows/scrape.yml`

Click **Run workflow** → leave branch as `main` → **Run workflow**.

- [ ] **Step 2: Watch the run to completion**

Click into the running job. Confirm each step succeeds:

1. **Check out repository** — green.
2. **Set up Python** — green; logs show Python 3.12 installed.
3. **Install dependencies** — green; logs show `requests` and `python-dotenv` installed.
4. **Run scraper** — green; logs show `Firecrawl returned 5 results` and five `wrote knowledge/raw/...` lines. If this step fails with a 401, the secret value was wrong — go back to Task 4 Step 2.
5. **Commit scraped files** — green; logs show either `No changes to commit` (rare on first run) or a commit + push.

- [ ] **Step 3: Confirm the commit on `main`**

Run:

```bash
git fetch origin
git log origin/main --oneline -5 --author='github-actions'
```

Expected: at least one commit authored by `github-actions[bot]` with subject `chore(scrape): update knowledge/raw (...)`.

If the workflow logged "No changes to commit" instead, that is also a valid pass — it means the script ran successfully but produced byte-identical files, which is unusual on a first run but not a failure.

- [ ] **Step 4: Pull the auto-commit locally**

Run:

```bash
git pull --ff-only origin main
ls knowledge/raw/
```

Expected: `knowledge/raw/` contains five `.md` files.

---

### Task 6: Confirm the schedule is registered

**Files:** none

- [ ] **Step 1: Verify the next scheduled run is shown**

Navigate to:
`https://github.com/nchabot14/chipotle-scrape-pipeline/actions/workflows/scrape.yml`

Expected: The page shows past runs (including the manual run from Task 5) and the workflow is enabled. GitHub does not display a "next run" countdown, but the cron line in the YAML (`"0 13 * * *"`) is the source of truth — the daily run will occur within a few minutes of 13:00 UTC.

- [ ] **Step 2: Note the verification window**

After ~24 hours, return to the Actions page and confirm a new run appears under "schedule" trigger (not "workflow_dispatch"). If no scheduled run has fired by 14:00 UTC the next day, check that the repo has had a recent commit on the default branch — GitHub disables `schedule` triggers on repos with no activity for 60 days, but this is a fresh repo so it should be fine.

---

## Acceptance criteria (from spec)

After completing all tasks:

1. Workflow runs successfully end-to-end on `workflow_dispatch` with only `FIRECRAWL_API_KEY` configured. **(verified in Task 5)**
2. Manual run via the Actions UI commits any resulting changes. **(Task 5 Step 3)**
3. A no-diff run completes successfully without a commit. *(will verify naturally on a future run; the script logic is the bot-skip clause in Task 2)*
4. A diff run pushes exactly one commit by `github-actions[bot]` and does not re-trigger the workflow. **(Task 5 Step 3 — to confirm no re-trigger, after the auto-commit lands, check the Actions tab and verify no new run was queued by the auto-commit push)**
5. A failure inside `scrape_pipeline.py` causes the job to fail red. *(failure-mode is structural; not exercised in happy-path verification)*
