#!/usr/bin/env python3
"""
Generate README.md from resume.json.

- Reads the single source of truth: resume.json
- Auto-pulls the user's PUBLIC GitHub repositories (name, description) via the
  GitHub REST API so new projects appear automatically.
- Repos that have a curated entry in resume.json render with a rich title, meta
  line and detailed bullets; repos without one fall back to their GitHub
  description.
- Renders a clean, light, print-friendly README.md.

Run locally (stdonly only, no pip deps):
    python3 scripts/build_readme.py

Or let GitHub Actions run it (see .github/workflows/update-profile.yml).
"""
import json
import os
import urllib.request
import urllib.parse
import datetime

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "resume.json")
OUT = os.path.join(HERE, "README.md")

API = "https://api.github.com"
ENV_TOKEN = "GITHUB_TOKEN"      # optional; avoids rate limits in CI


def github_api(path):
    req = urllib.request.Request(API + path, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "resume-builder",
    })
    token = os.environ.get(ENV_TOKEN)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.load(r)
    except Exception as e:           # noqa: BLE001
        print(f"  ! API call {path} failed: {e}")
        return None


def load_data():
    with open(DATA, encoding="utf-8") as f:
        return json.load(f)


def fetch_repos(username, exclude):
    print(f"  → fetching public repos for {username}...")
    repos = github_api(f"/users/{urllib.parse.quote(username)}/repos?per_page=100&sort=pushed")
    if repos is None:
        return []
    out = []
    for r in repos:
        if r.get("fork") or r.get("archived"):
            continue
        if r["name"].lower() in [e.lower() for e in exclude]:
            continue
        out.append({
            "name": r["name"],
            "url": r["html_url"],
            "description": (r.get("description") or "").strip(),
        })
    return out


def esc(s):
    # Escape markdown link/table-breaking characters only where needed.
    return (s or "").replace("|", "\\|").strip()


def xml_escape(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_radar(benchmark, path, accent="#7c3aed", target="#059669"):
    """
    Generate a clean, light-theme SVG radar chart comparing 'me' vs a benchmark.
    Written to `path` so the README can embed it as an image (GitHub strips JS,
    so the chart must be a generated image). Returns True on success.
    """
    axes = benchmark.get("axes", [])
    if not axes:
        return False
    import math
    n = len(axes)
    # Extra bottom padding for the legend; generous side padding so the
    # multi-word axis labels don't overflow (labels anchor outward).
    cx, cy, R = 300, 250, 168
    W, H = 700, 560
    me_label = benchmark.get("me_label", "Me")
    target_label = benchmark.get("target_label", "Target")

    def pt(i, radius):
        ang = 2 * math.pi * i / n - math.pi / 2
        return (cx + radius * math.cos(ang), cy + radius * math.sin(ang))

    def poly(scale):
        return " ".join(f"{pt(i, R * scale)[0]:.1f},{pt(i, R * scale)[1]:.1f}" for i in range(n))

    out = []
    out.append('<?xml version="1.0" encoding="UTF-8"?>')
    out.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
               f'width="{W}" height="{H}" role="img" aria-label="Skills radar chart comparing {xml_escape(me_label)} to {xml_escape(target_label)}">')
    # grid rings
    out.append('  <g fill="none" stroke="#e2e8f0">')
    for r in (0.2, 0.4, 0.6, 0.8, 1.0):
        out.append(f'    <polygon points="{poly(r)}" stroke-width="{1.4 if r == 1.0 else 1}"/>')
    out.append('  </g>')
    # spokes
    out.append('  <g stroke="#e2e8f0" stroke-width="1">')
    for i in range(n):
        x, y = pt(i, R)
        out.append(f'    <line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}"/>')
    out.append('  </g>')
    # axis labels
    out.append('  <g fill="#475569" font-family="Segoe UI, Arial, sans-serif" font-size="13" font-weight="600">')
    for i, a in enumerate(axes):
        x, y = pt(i, R + 46)
        anchor = "middle"
        if abs(x - cx) < 55:
            anchor = "middle"
        elif x > cx:
            anchor = "start"           # right side -> text extends right
        else:
            anchor = "end"             # left side -> text extends left
        if y < cy and abs(x - cx) < 55:
            anchor = "middle"
        # keep labels inside the canvas (left/right overflow)
        x = max(16, min(W - 16, x))
        out.append(f'    <text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" dominant-baseline="middle">{xml_escape(a["skill"])}</text>')
    out.append('  </g>')
    # target polygon (benchmark) — solid fill, accent border
    tp = " ".join(f"{pt(i, R * axes[i]['target'] / 100)[0]:.1f},{pt(i, R * axes[i]['target'] / 100)[1]:.1f}" for i in range(n))
    mp = " ".join(f"{pt(i, R * axes[i]['me'] / 100)[0]:.1f},{pt(i, R * axes[i]['me'] / 100)[1]:.1f}" for i in range(n))
    out.append(f'  <polygon points="{tp}" fill="{target}" fill-opacity="0.14" stroke="{target}" stroke-width="2" stroke-linejoin="round"/>')
    out.append(f'  <polygon points="{mp}" fill="{accent}" fill-opacity="0.30" stroke="{accent}" stroke-width="2.5" stroke-linejoin="round"/>')
    # dots on my polygon
    out.append(f'  <g fill="{accent}">')
    for i in range(n):
        x, y = pt(i, R * axes[i]['me'] / 100)
        out.append(f'    <circle cx="{x:.1f}" cy="{y:.1f}" r="3.5"/>')
    out.append('  </g>')
    # legend — centered along the bottom, tucked under the chart where it's clear
    out.append('  <g font-family="Segoe UI, Arial, sans-serif" font-size="14">')
    # approximate lengths to centre the whole legend group
    w_me = len(me_label) * 7.2 + 22
    w_tg = len(target_label) * 7.2 + 22
    total = w_me + 50 + w_tg
    start = cx - total / 2
    ly = H - 26
    me_x = start
    tg_x = start + w_me + 50
    out.append(f'    <rect x="{me_x:.0f}" y="{ly-12}" width="16" height="16" rx="3" fill="{accent}" fill-opacity="0.30" stroke="{accent}"/>')
    out.append(f'    <text x="{me_x+22:.0f}" y="{ly}" fill="#334155">{xml_escape(me_label)}</text>')
    out.append(f'    <rect x="{tg_x:.0f}" y="{ly-12}" width="16" height="16" rx="3" fill="{target}" fill-opacity="0.14" stroke="{target}"/>')
    out.append(f'    <text x="{tg_x+22:.0f}" y="{ly}" fill="#334155">{xml_escape(target_label)}</text>')
    out.append('  </g>')
    out.append('</svg>')
    svg = "\n".join(out)
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)
    return True


def render_project(repo, curated):
    """Return a rich project block given a repo dict + optional curated dict."""
    name = repo["name"]
    if curated:
        title = curated.get("title", name)
        meta = curated.get("meta", "")
        bullets = curated.get("bullets", [])
        head = f"#### [{esc(title)}]({repo['url']})"
        if meta:
            head += f" · <sub>{esc(meta)}</sub>"
        body = "\n".join(f"- {esc(b)}" for b in bullets)
        if not body:
            body = f"- {esc(repo['description']) or '—'}"
        return f"{head}\n{body}"
    # Fallback: GitHub one-liner
    desc = repo["description"] or "—"
    return f"#### [{esc(name)}]({repo['url']})\n- {esc(desc)}"


def render(data, repo_meta):
    p = data["profile"]; c = p["contact"]
    ex = data["experience"]
    ed = data["education"]
    certs = data["certifications"]
    training = data.get("additional_training", [])
    details = data.get("details", {})
    skills = data["skills"]
    curated = data["projects"].get("curated", {})
    username = c.get("github_username")

    # Order: curated (substantive) projects first in resume.json order, then
    # any newly auto-pulled repos (by most-recently-pushed).
    curated_order = list(curated.keys())
    rank = {name: i for i, name in enumerate(curated_order)}
    repo_meta.sort(key=lambda r: (rank.get(r["name"], 10**6), r["name"]))

    projects = "\n\n".join(render_project(r, curated.get(r["name"])) for r in repo_meta)
    n_projects = len(repo_meta)

    def exp_list(entries):
        if not entries:
            return "_Add your experience in resume.json._"
        parts = []
        for e in entries:
            span = " — ".join(x for x in [e.get("start"), e.get("end")] if x)
            meta = ", ".join(x for x in [esc(e.get("company")), esc(e.get("location")), span] if x)
            parts.append(f"**{esc(e['role'])}**  \n{meta}")
            for b in e.get("bullets", []):
                parts.append(f"- {esc(b)}")
        return "\n\n".join(parts)

    def edu_list(entries):
        if not entries:
            return "_Add your education in resume.json._"
        return "\n\n".join(
            f"**{esc(e.get('degree'))}**  \n{esc(e.get('school'))} · {esc(e.get('years'))}"
            for e in entries)

    def skill_blocks(sk):
        return "\n\n".join(
            f"**{cat}**  \n{', '.join(f'`{esc(x)}`' for x in items)}"
            for cat, items in sk.items())

    contact_links = [f'<a href="{c["github"]}">GitHub</a>']
    if c.get("linkedin"):
        contact_links.append(f'<a href="{c["linkedin"]}">LinkedIn</a>')
    if c.get("email"):
        contact_links.append(f'<a href="mailto:{c["email"]}">{c["email"]}</a>')
    if c.get("phone"):
        contact_links.append(c["phone"])
    if c.get("portfolio"):
        contact_links.append(f'<a href="{c["portfolio"]}">Portfolio</a>')
    contact_line = " · ".join(contact_links)

    # Build the benchmark radar SVG (generated image) if benchmark data exists.
    benchmark_md = ""
    benchmark = data.get("benchmark")
    same_dir_svg = os.path.join(HERE, "skills-radar.svg")
    rail = os.path.relpath(same_dir_svg, HERE)
    if benchmark and benchmark.get("axes"):
        if render_radar(benchmark, same_dir_svg):
            title = esc(benchmark.get("title", "Skills vs. benchmark"))
            benchmark_md = f"""### 📊 Skills Benchmark

_{title} — {esc(benchmark.get('me_label','Me'))} vs. {esc(benchmark.get('target_label','Target'))}._

<p align="center">
  <img src="{rail}" width="700" alt="Skills benchmark radar chart"/>
</p>

"""

    # Optional footer details (only non-empty)
    detail_lines = []
    if details.get("target_roles"):
        detail_lines.append(f"**Target roles:** {esc(details['target_roles'])}")
    if details.get("availability"):
        detail_lines.append(f"**Availability:** {esc(details['availability'])}")
    if details.get("languages"):
        detail_lines.append(f"**Languages:** {esc(details['languages'])}")
    details_md = "\n\n".join(detail_lines)

    training_md = "\n".join(f"- {esc(t)}" for t in training) if training else ""

    gen = datetime.date.today().isoformat()
    avatar = f'<img src="https://github.com/{username}.png?size=160" width="88" height="88" alt="profile" />' if username else ""

    md = f"""<!-- AUTO-GENERATED from resume.json — do not edit by hand. -->
<div align="center">
{avatar}
<h1>{esc(p['name'])}</h1>
<p><b>{esc(p['title'])}</b><br/>{esc(p['location'])}</p>
<p>{contact_line}</p>
</div>

> {esc(p['tagline'])}

---

### 💼 Experience

{exp_list(ex['entries'])}

---

{benchmark_md}### 🛠️ Skills

{skill_blocks(skills)}

---

### 🚀 Projects

_{n_projects} public repositories — populated automatically from GitHub._

{projects}

---

### 🎓 Certifications

{chr(10).join(f'- {esc(x)}' for x in certs)}

### 📚 Education

{edu_list(ed['entries'])}

### 🎯 Details

{details_md}

---

<div align="center">
<sub><i>Rendered from <code>resume.json</code> on {gen}. Edit the JSON (or push new repos) and this updates automatically.</i></sub>
</div>
"""
    return md


def main():
    print("Building README.md from resume.json ...")
    data = load_data()
    username = data["profile"]["contact"].get("github_username")
    exclude = data["projects"].get("exclude", [])
    repo_meta = fetch_repos(username, exclude) if username else []
    md = render(data, repo_meta)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"  ✓ wrote {OUT} ({len(md)} bytes, {len(repo_meta)} repos)")


if __name__ == "__main__":
    main()
