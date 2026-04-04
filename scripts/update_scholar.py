"""Fetch Google Scholar citation data via SerpAPI and render a dracula-themed
PNG matching the style of Scholar's own "Cited by" card.

Writes assets/google_scholar_profile.png.

Env:
    SERPAPI_KEY     SerpAPI API key
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
OUT = ROOT / "assets" / "google_scholar_profile.png"

# Dracula palette
BG = "#282a36"
FG = "#f8f8f2"
COMMENT = "#6272a4"
PURPLE = "#bd93f9"
PINK = "#ff79c6"
GREEN = "#50fa7b"
CURRENT_LINE = "#44475a"

AUTHOR_ID = os.environ.get("SCHOLAR_AUTHOR", "KxJU37kAAAAJ")
API_KEY = os.environ.get("SERPAPI_KEY", "")


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


def _render(data: dict) -> None:
    table = data["cited_by"]["table"]
    # Keys look like {"citations": {"all":..., "since_2021":...}}
    def _pair(entry: dict, key: str) -> tuple[int, int]:
        sub = entry[key]
        all_val = sub["all"]
        since_val = next(v for k, v in sub.items() if k.startswith("since_"))
        since_label = next(k for k in sub if k.startswith("since_"))
        return all_val, since_val, since_label.replace("since_", "Since ")

    citations_all, citations_since, since_label = _pair(table[0], "citations")
    h_all, h_since, _ = _pair(table[1], "h_index")
    i10_all, i10_since, _ = _pair(table[2], "i10_index")

    graph = data["cited_by"]["graph"]
    years = [entry["year"] for entry in graph]
    counts = [entry["citations"] for entry in graph]

    fig = plt.figure(figsize=(6.0, 4.4), dpi=140, facecolor=BG)
    gs = fig.add_gridspec(2, 1, height_ratios=[1.1, 2.2], hspace=0.35)

    # --- stats table ---
    ax_t = fig.add_subplot(gs[0])
    ax_t.set_facecolor(BG)
    ax_t.axis("off")
    rows = [
        ("Citations", citations_all, citations_since),
        ("h-index", h_all, h_since),
        ("i10-index", i10_all, i10_since),
    ]
    col_labels = ["", "All", since_label]
    table_data = [[r[0], f"{r[1]:,}", f"{r[2]:,}"] for r in rows]
    tbl = ax_t.table(
        cellText=table_data,
        colLabels=col_labels,
        cellLoc="center",
        loc="center",
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(11)
    tbl.scale(1, 1.4)
    for (r, c), cell in tbl.get_celld().items():
        cell.set_edgecolor(CURRENT_LINE)
        cell.set_facecolor(BG)
        txt = cell.get_text()
        if r == 0:
            txt.set_color(COMMENT)
            txt.set_fontweight("bold")
        elif c == 0:
            txt.set_color(PURPLE)
            txt.set_fontweight("bold")
        else:
            txt.set_color(FG)

    # --- bar chart ---
    ax = fig.add_subplot(gs[1])
    ax.set_facecolor(BG)
    bars = ax.bar(years, counts, color=PURPLE, edgecolor=PINK, linewidth=0.6)
    ax.tick_params(colors=FG, labelsize=9)
    for spine in ax.spines.values():
        spine.set_color(CURRENT_LINE)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_title(
        f"Citations per year  (retrieved {_dt.date.today():%Y-%m-%d})",
        color=FG, fontsize=11, pad=8,
    )
    ax.grid(axis="y", color=CURRENT_LINE, linewidth=0.5, alpha=0.6)
    ax.set_axisbelow(True)
    for bar in bars:
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{int(bar.get_height())}",
            ha="center", va="bottom",
            color=GREEN, fontsize=8, fontweight="bold",
        )

    fig.tight_layout()
    OUT.parent.mkdir(exist_ok=True)
    fig.savefig(OUT, facecolor=BG)
    plt.close(fig)
    print(f"wrote {OUT}")


def main() -> int:
    data = _fetch()
    _render(data)
    return 0


if __name__ == "__main__":
    sys.exit(main())
