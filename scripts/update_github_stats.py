"""Fetch GitHub stats via the REST API and render light+dark PNG cards.

Outputs:
    assets/github_stats_light.png
    assets/github_stats_dark.png
    assets/github_langs_light.png
    assets/github_langs_dark.png

Env:
    GITHUB_USER     GitHub username (default: inkyusa)
    GITHUB_TOKEN    Optional; higher rate limits (Actions provides this).
"""

from __future__ import annotations

import os
import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import requests

ROOT = pathlib.Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"

USER = os.environ.get("GITHUB_USER", "inkyusa")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
API = "https://api.github.com"

THEMES = {
    "light": {
        "bg": "#ffffff",
        "fg": "#1f2328",
        "muted": "#656d76",
        "grid": "#eaeef2",
        "primary": "#0969da",
        "accent": "#8250df",
        "border": "#d0d7de",
    },
    "dark": {
        "bg": "#0d1117",
        "fg": "#e6edf3",
        "muted": "#8b949e",
        "grid": "#21262d",
        "primary": "#58a6ff",
        "accent": "#bc8cff",
        "border": "#30363d",
    },
}

# A small curated palette for language segments (GitHub colors).
LANG_COLORS = {
    "Python": "#3572A5",
    "C++": "#f34b7d",
    "Jupyter Notebook": "#DA5B0B",
    "MATLAB": "#e16737",
    "Shell": "#89e051",
    "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6",
    "HTML": "#e34c26",
    "CSS": "#563d7c",
    "CMake": "#DA3434",
    "Makefile": "#427819",
    "Dockerfile": "#384d54",
    "Lua": "#000080",
    "C": "#555555",
    "Go": "#00ADD8",
    "Rust": "#dea584",
    "Cuda": "#3A4E3A",
}


def _headers() -> dict:
    h = {"Accept": "application/vnd.github+json"}
    if TOKEN:
        h["Authorization"] = f"Bearer {TOKEN}"
    return h


def _get(path: str, **params) -> object:
    r = requests.get(f"{API}{path}", headers=_headers(), params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def _fetch_stats() -> dict:
    user = _get(f"/users/{USER}")
    repos = []
    page = 1
    while True:
        batch = _get(f"/users/{USER}/repos", per_page=100, page=page, sort="updated")
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
        if page > 20:
            break

    own = [r for r in repos if not r.get("fork")]
    stars = sum(r.get("stargazers_count", 0) for r in own)
    forks = sum(r.get("forks_count", 0) for r in own)

    # Aggregate bytes per language for non-fork repos (parallelizable but
    # kept sequential for simplicity; ~20-60 HTTP calls with token is fine).
    lang_bytes: dict[str, int] = {}
    for r in own:
        try:
            langs = _get(f"/repos/{USER}/{r['name']}/languages")
        except Exception:
            continue
        for lang, n in langs.items():
            lang_bytes[lang] = lang_bytes.get(lang, 0) + int(n)

    return {
        "name": user.get("name") or USER,
        "followers": user.get("followers", 0),
        "following": user.get("following", 0),
        "public_repos": user.get("public_repos", 0),
        "own_repos": len(own),
        "stars": stars,
        "forks": forks,
        "lang_bytes": lang_bytes,
    }


def _render_stats_card(stats: dict, theme: str) -> None:
    t = THEMES[theme]
    fig = plt.figure(figsize=(6.0, 2.6), dpi=160, facecolor=t["bg"])

    fig.text(
        0.04, 0.86,
        f"{stats['name']} · GitHub",
        color=t["fg"], fontsize=13, fontweight="bold",
    )

    kpis = [
        ("Stars", stats["stars"]),
        ("Repos", stats["public_repos"]),
        ("Followers", stats["followers"]),
        ("Forks", stats["forks"]),
    ]
    x_positions = [0.06, 0.30, 0.54, 0.78]
    for (label, val), x in zip(kpis, x_positions):
        fig.text(x, 0.45, f"{val:,}", color=t["primary"],
                 fontsize=22, fontweight="bold")
        fig.text(x, 0.25, label, color=t["muted"], fontsize=9)

    # Thin separator rule at the top under title
    ax = fig.add_axes([0.04, 0.78, 0.92, 0.003])
    ax.set_facecolor(t["border"]); ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)

    out = ASSETS / f"github_stats_{theme}.png"
    fig.savefig(out, facecolor=t["bg"])
    plt.close(fig)
    print(f"wrote {out}")


def _render_langs_card(stats: dict, theme: str) -> None:
    t = THEMES[theme]
    lang_bytes = stats["lang_bytes"]
    total = sum(lang_bytes.values()) or 1
    top = sorted(lang_bytes.items(), key=lambda kv: kv[1], reverse=True)[:8]

    fig = plt.figure(figsize=(4.0, 2.8), dpi=160, facecolor=t["bg"])
    fig.text(
        0.06, 0.88,
        "Top languages",
        color=t["fg"], fontsize=12, fontweight="bold",
    )

    # Stacked horizontal bar
    ax = fig.add_axes([0.06, 0.68, 0.88, 0.10])
    ax.set_facecolor(t["bg"])
    x = 0.0
    for lang, n in top:
        w = n / total
        ax.barh(0, w, left=x, height=1.0,
                color=LANG_COLORS.get(lang, t["accent"]))
        x += w
    ax.set_xlim(0, 1); ax.set_ylim(-0.5, 0.5)
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)

    # Legend grid
    legend_top = 0.58
    row_h = 0.085
    for i, (lang, n) in enumerate(top):
        col = i % 2
        row = i // 2
        x0 = 0.06 + col * 0.47
        y0 = legend_top - row * row_h
        fig.patches.append(plt.Rectangle(
            (x0, y0), 0.018, 0.04,
            transform=fig.transFigure,
            color=LANG_COLORS.get(lang, t["accent"]),
        ))
        pct = n / total * 100
        fig.text(x0 + 0.028, y0 + 0.012,
                 f"{lang}", color=t["fg"], fontsize=8, fontweight="medium")
        fig.text(x0 + 0.40, y0 + 0.012,
                 f"{pct:4.1f}%", color=t["muted"], fontsize=8, ha="right")

    out = ASSETS / f"github_langs_{theme}.png"
    fig.savefig(out, facecolor=t["bg"])
    plt.close(fig)
    print(f"wrote {out}")


def main() -> int:
    ASSETS.mkdir(exist_ok=True)
    stats = _fetch_stats()
    for theme in THEMES:
        _render_stats_card(stats, theme)
        _render_langs_card(stats, theme)
    return 0


if __name__ == "__main__":
    sys.exit(main())
