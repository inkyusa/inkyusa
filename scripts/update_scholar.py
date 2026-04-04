"""Fetch Google Scholar citation data via SerpAPI and render two PNG cards
(light and dark) styled to match GitHub's native aesthetic.

Outputs:
    assets/scholar_light.png
    assets/scholar_dark.png

Env:
    SERPAPI_KEY     SerpAPI API key (required)
    SCHOLAR_AUTHOR  Google Scholar author id (default: KxJU37kAAAAJ)
"""

from __future__ import annotations

import datetime as _dt
import os
import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import requests

ROOT = pathlib.Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"

AUTHOR_ID = os.environ.get("SCHOLAR_AUTHOR", "KxJU37kAAAAJ")
API_KEY = os.environ.get("SERPAPI_KEY", "")

THEMES = {
    "light": {
        "bg": "#ffffff",
        "fg": "#1f2328",
        "muted": "#656d76",
        "border": "#d0d7de",
        "grid": "#eaeef2",
        "primary": "#0969da",
        "accent": "#8250df",
        "label": "#0969da",
    },
    "dark": {
        "bg": "#0d1117",
        "fg": "#e6edf3",
        "muted": "#8b949e",
        "border": "#30363d",
        "grid": "#21262d",
        "primary": "#58a6ff",
        "accent": "#bc8cff",
        "label": "#7ee787",
    },
}


def _fetch() -> dict:
    if not API_KEY:
        raise SystemExit("SERPAPI_KEY is required")
    resp = requests.get(
        "https://serpapi.com/search.json",
        params={
            "engine": "google_scholar_author",
            "author_id": AUTHOR_ID,
            "api_key": API_KEY,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise SystemExit(f"SerpAPI error: {data['error']}")
    return data


def _extract_stats(data: dict):
    table = data["cited_by"]["table"]

    def pair(entry, key):
        sub = entry[key]
        all_val = sub["all"]
        since_label = next(k for k in sub if k.startswith("since_"))
        since_val = sub[since_label]
        return all_val, since_val, since_label.replace("since_", "Since ")

    c_all, c_since, since_label = pair(table[0], "citations")
    h_all, h_since, _ = pair(table[1], "h_index")
    i_all, i_since, _ = pair(table[2], "i10_index")

    graph = data["cited_by"]["graph"]
    years = [e["year"] for e in graph]
    counts = [e["citations"] for e in graph]
    return {
        "citations": (c_all, c_since),
        "h_index": (h_all, h_since),
        "i10_index": (i_all, i_since),
        "since_label": since_label,
        "years": years,
        "counts": counts,
    }


def _render(stats: dict, theme_name: str) -> pathlib.Path:
    t = THEMES[theme_name]
    fig = plt.figure(figsize=(7.2, 4.0), dpi=160, facecolor=t["bg"])
    gs = fig.add_gridspec(
        2, 3,
        height_ratios=[1, 2.6],
        hspace=0.5, wspace=0.25,
        left=0.07, right=0.97, top=0.9, bottom=0.13,
    )

    # --- KPI cards ---
    kpis = [
        ("Citations", stats["citations"]),
        ("h-index", stats["h_index"]),
        ("i10-index", stats["i10_index"]),
    ]
    for i, (name, (all_v, since_v)) in enumerate(kpis):
        ax = fig.add_subplot(gs[0, i])
        ax.set_facecolor(t["bg"])
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.set_xticks([]); ax.set_yticks([])
        ax.set_xlim(0, 1); ax.set_ylim(0, 1)
        ax.text(0.5, 0.82, name, ha="center", va="center",
                color=t["muted"], fontsize=10, fontweight="medium")
        ax.text(0.5, 0.45, f"{all_v:,}", ha="center", va="center",
                color=t["primary"], fontsize=22, fontweight="bold")
        ax.text(0.5, 0.08, f"{stats['since_label']}: {since_v:,}",
                ha="center", va="center",
                color=t["muted"], fontsize=8)

    # --- bar chart ---
    ax = fig.add_subplot(gs[1, :])
    ax.set_facecolor(t["bg"])
    years = stats["years"]
    counts = stats["counts"]
    bars = ax.bar(
        years, counts,
        color=t["primary"], width=0.72,
        edgecolor="none",
    )
    ax.set_title(
        "Citations per year",
        color=t["fg"], fontsize=11, fontweight="bold",
        loc="left", pad=8,
    )
    ax.tick_params(colors=t["muted"], labelsize=8, length=0)
    ax.grid(axis="y", color=t["grid"], linewidth=0.8, alpha=1.0)
    ax.set_axisbelow(True)
    for spine_name, spine in ax.spines.items():
        spine.set_visible(spine_name == "bottom")
        if spine_name == "bottom":
            spine.set_color(t["border"])
            spine.set_linewidth(0.8)
    for bar, val in zip(bars, counts):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(counts) * 0.015,
            f"{val}",
            ha="center", va="bottom",
            color=t["label"], fontsize=7, fontweight="bold",
        )

    # --- footer ---
    fig.text(
        0.97, 0.02,
        f"Updated {_dt.date.today():%Y-%m-%d} · scholar.google.com",
        ha="right", va="bottom",
        color=t["muted"], fontsize=7,
    )

    out = ASSETS / f"scholar_{theme_name}.png"
    fig.savefig(out, facecolor=t["bg"])
    plt.close(fig)
    print(f"wrote {out}")
    return out


def main() -> int:
    ASSETS.mkdir(exist_ok=True)
    data = _fetch()
    stats = _extract_stats(data)
    for theme in THEMES:
        _render(stats, theme)
    return 0


if __name__ == "__main__":
    sys.exit(main())
