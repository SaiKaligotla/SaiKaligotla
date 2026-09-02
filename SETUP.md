# Setup Guide

This folder is a **self-updating resume profile** for GitHub. Content comes from your
actual resume (Sai_Kaligotla_SOC_Analyst_Resume_FULL.pdf), loaded into the single data
file below.

## Files

| File | Purpose |
|------|---------|
| `resume.json` | **Single source of truth.** All real content lives here. Edit this to update anything. |
| `scripts/build_readme.py` | The generator. Reads `resume.json` + GitHub API → writes `README.md`. Pure Python stdlib (no `pip install`). |
| `.github/workflows/update-profile.yml` | GitHub Action that re-runs the generator on edit / schedule / manual. |
| `README.md` | **The output.** Auto-generated — don't hand-edit. This is what people see on your GitHub profile. |
| `skills-radar.svg` | **Generated.** Skills benchmark radar chart (Me vs. senior benchmark). Auto-created by the build from `benchmark` data in `resume.json`. Don't hand-edit. |
| `LICENSE` | MIT license (in your name). |

## How to publish it as your GitHub profile

1. Create a repo named **exactly `SaiKaligotla`** (the special profile repo). Make it
   **public** and tick **"Add a README file"**.
2. Copy everything from this folder in (replace the default README).
3. Push to `main`.
4. On the **Actions** tab run **"Auto-update profile README"** once manually to generate
   immediately (or just edit `resume.json` — that triggers it automatically).

> GitHub only shows the profile README for the repo named after your username. To keep
> your live production work private, note that your **vendor/tool repos are public** and
> will be auto-listed unless added to `projects.exclude` in resume.json.

## How auto-update works

| Trigger | What happens |
|---------|--------------|
| Push a change to `resume.json` | Workflow regenerates `README.md` and commits it. |
| Push a **new public repo** | The daily run (or manual) re-pulls your repos and adds it to Projects. |
| Cron (`0 8 * * *`) | Rebuilds daily. |
| Manual "Run workflow" | Rebuild on demand. |

## How it's organised

- **Benchmark radar chart** (`benchmark` in `resume.json`): compares your current skill
  level (purple) to a **senior SOC Analyst benchmark** (green) across 10 core areas.
  Edit the `me`/`target` values (0–100) and the chart regenerates automatically on the
  next build. Add or remove axes; the chart colours and labels update.

- **Projects** are auto-pulled from your public GitHub. Repos that have a matching entry
  under `projects.curated` in `resume.json` render with a rich title, meta line and the
  detailed bullets from your resume (SOC Home Lab, LetsDefend case files, Deloitte,
  Mastercard, Botium, SQL, Linux, etc.). Any repo you push **without** a curated entry
  still appears automatically using its GitHub description. Add repo names to
  `projects.exclude` to hide them.
- **Order** is: curated projects first (in the order they appear in `resume.json`), then
  new auto-added repos.

## Regenerate locally

```bash
python3 scripts/build_readme.py
```

Requires only Python 3. The `pypdf` package is only needed if you re-read the PDF.
