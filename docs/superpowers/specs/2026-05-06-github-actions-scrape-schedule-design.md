# GitHub Actions schedule for the Firecrawl scrape pipeline

## Goal

Run `scrape_pipeline.py` automatically on a daily schedule via GitHub Actions, and commit any new or changed files in `knowledge/raw/` back to `main`. The workflow can also be triggered manually from the Actions UI.

## Context

The repo currently has one script, `scrape_pipeline.py`, which calls the Firecrawl `/v2/search` endpoint for "Chipotle investor relations press releases", takes the top 5 results, and writes each as a markdown file with frontmatter into `knowledge/raw/`. The script reads its API key from the environment variable `API_KEY` (loaded from a local `.env` via `python-dotenv`). Dependencies today are `requests` and `python-dotenv`. There is no `requirements.txt` and no existing workflow.

The repo's GitHub remote is `nchabot14/chipotle-scrape-pipeline`. The `knowledge/raw/` directory is tracked by git (not in `.gitignore`).

## Files added

- `.github/workflows/scrape.yml` — the scheduled workflow.
- `requirements.txt` — pins `requests` and `python-dotenv`.

`scrape_pipeline.py` is unchanged. The `load_dotenv()` call is a no-op in CI (no `.env` present), and the script already reads `API_KEY` from `os.environ`, so the workflow's `env:` block is sufficient.

## Workflow design

### Triggers

```yaml
on:
  schedule:
    - cron: "0 13 * * *"   # 13:00 UTC daily
  workflow_dispatch:
```

13:00 UTC corresponds to roughly 8am Central (DST) / 7am Central (standard). GitHub may delay scheduled runs by several minutes under load; that is acceptable for a daily press-release scrape. `workflow_dispatch` adds a "Run workflow" button for ad-hoc testing.

### Permissions

The job needs `contents: write` so the default `GITHUB_TOKEN` can push the auto-commit.

### Job steps

A single job on `ubuntu-latest` with these steps:

1. `actions/checkout@v4`.
2. `actions/setup-python@v5` with `python-version: "3.12"` and `cache: pip` keyed off `requirements.txt`.
3. `pip install -r requirements.txt`.
4. Run the scraper:
   ```yaml
   - name: Run scraper
     env:
       API_KEY: ${{ secrets.FIRECRAWL_API_KEY }}
     run: python scrape_pipeline.py
   ```
5. Commit and push any changes under `knowledge/raw/` (see next section).

### Commit-back step

```yaml
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

Behavior:

- **Idempotent / overwrite semantics.** The script always rewrites each file. If only the `scraped_at` frontmatter field changes, that still counts as a diff and is committed — this gives a daily "heartbeat" in git history. This matches the user's chosen re-scrape behavior ("overwrite every time").
- **Skip-if-empty.** If there is no diff (e.g. Firecrawl returned identical content and somehow `scraped_at` did not change, or earlier steps produced no files), the step exits 0 with a log line and no commit.
- **No workflow loop.** Pushes authored by the default `GITHUB_TOKEN` do not trigger workflow runs, so the auto-commit cannot kick off another scheduled run.

## Secrets

One repository secret is required:

- `FIRECRAWL_API_KEY` — the Firecrawl API key. Set in GitHub → Settings → Secrets and variables → Actions.

The workflow maps it into the step environment as `API_KEY`, which is the variable name the script reads.

The local `.env` file remains the developer-machine source of truth and is unaffected.

## Dependencies

`requirements.txt` will pin the two current runtime dependencies:

```
requests
python-dotenv
```

Versions can be left unpinned initially; if reproducibility becomes important, switch to `pip-compile` or version pins later.

## Error handling

- If `python scrape_pipeline.py` fails (Firecrawl outage, invalid key, network error, malformed response), the step exits non-zero, the job fails, and GitHub emails the repo owner. No retry logic is added — a daily failure email is sufficient alerting for this pipeline.
- The script does not currently check `response.ok` before reading `data["data"]["web"]`. A non-200 response will raise `KeyError` and fail the step loudly, which is the desired behavior. Tightening this is out of scope for this change.
- `knowledge/raw/` must remain tracked by git for the commit-back to work. It already is.

## Out of scope

- Changes to scraping logic (query, result limit, formats, dedup behavior).
- Avoiding frontmatter-only diffs (e.g. only rewriting files when the body changes).
- Pinning dependency versions.
- Notifications beyond GitHub's default email-on-failure.
- Branch protection / PR-based merging of scraped content.

## Acceptance criteria

1. Pushing the workflow + `requirements.txt` to `main` and adding the `FIRECRAWL_API_KEY` secret is sufficient to make the daily run succeed end-to-end.
2. A manual run via the Actions UI ("Run workflow") performs the same steps and commits any resulting changes.
3. When `knowledge/raw/` has no diff after a run, the job completes successfully with no new commit.
4. When `knowledge/raw/` has a diff, exactly one commit is pushed to `main` authored by `github-actions[bot]`, and that commit does not trigger another workflow run.
5. A failure inside `scrape_pipeline.py` causes the job to fail (red check on the run).
