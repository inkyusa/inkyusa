"""Fetch Kaggle stats via the authenticated REST API and render light+dark
PNG cards matching the Scholar/GitHub aesthetic.

Outputs:
    assets/kaggle_light.png
    assets/kaggle_dark.png

Env:
    KAGGLE_USERNAME (required)
    KAGGLE_KEY      (required)
    KAGGLE_PROFILE  (default: same as KAGGLE_USERNAME)
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
from requests.auth import HTTPBasicAuth

ROOT = pathlib.Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"

USERNAME = os.environ.get("KAGGLE_USERNAME", "")
API_KEY = os.environ.get("KAGGLE_KEY", "")
PROFILE = os.environ.get("KAGGLE_PROFILE", USERNAME)

THEMES = {
    "light": {
        "bg": "#ffffff",
        "fg": "#1f2328",
        "muted": "#656d76",
        "border": "#d0d7de",
        "primary": "#20BEFF",   # Kaggle blue
        "accent":  "#0969da",
    },
    "dark": {
        "bg": "#0d1117",
        "fg": "#e6edf3",
        "muted": "#8b949e",
        "border": "#30363d",
        "primary": "#20BEFF",
        "accent":  "#58a6ff",
    },
}


def _paginate(path: str, params: dict, auth) -> list:
    out: list = []
    for page in range(1, 20):
        r = requests.get(
            f"https://www.kaggle.com/api/v1/{path}",
            auth=auth, params={**params, "page": page}, timeout=30,
        )
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        out.extend(batch)
        # Endpoints return variable page sizes; bail when the server
        # returns fewer than we asked for.
        if "page_size" in params and len(batch) < params["page_size"]:
            break
        if "page_size" not in params and len(batch) < 20:
            break
    return out


def _fetch() -> dict:
    if not (USERNAME and API_KEY):
        raise SystemExit("KAGGLE_USERNAME and KAGGLE_KEY are required")
    auth = HTTPBasicAuth(USERNAME, API_KEY)
    datasets = _paginate("datasets/list", {"user": PROFILE}, auth)
    notebooks = _paginate("kernels/list", {"user": PROFILE, "page_size": 100}, auth)

    ds_votes = sum(d.get("voteCount", 0) or 0 for d in datasets)
    ds_dl = sum(d.get("downloadCount", 0) or 0 for d in datasets)
    ds_views = sum(d.get("viewCount", 0) or 0 for d in datasets)
    nb_votes = sum(k.get("totalVotes", 0) or 0 for k in notebooks)

    return {
        "datasets": len(datasets),
        "notebooks": len(notebooks),
        "ds_votes": ds_votes,
        "ds_downloads": ds_dl,
        "ds_views": ds_views,
        "nb_votes": nb_votes,
        "total_votes": ds_votes + nb_votes,
    }


def _fmt(n: int) -> str:
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 10_000:
        return f"{n/1_000:.1f}k"
    if n >= 1_000:
        return f"{n:,}"
    return str(n)


def _render(stats: dict, theme: str) -> None:
    t = THEMES[theme]
    fig = plt.figure(figsize=(7.2, 2.8), dpi=160, facecolor=t["bg"])

    fig.text(
        0.05, 0.84,
        f"Kaggle · {PROFILE}",
        color=t["fg"], fontsize=13, fontweight="bold",
    )
    fig.text(
        0.95, 0.84,
        f"Updated {_dt.date.today():%Y-%m-%d}",
        color=t["muted"], fontsize=8, ha="right", va="baseline",
    )

    # Separator
    ax = fig.add_axes([0.05, 0.76, 0.90, 0.003])
    ax.set_facecolor(t["border"]); ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)

    kpis = [
        ("Datasets", stats["datasets"]),
        ("Notebooks", stats["notebooks"]),
        ("Votes",     stats["total_votes"]),
        ("Downloads", stats["ds_downloads"]),
    ]
    xs = [0.07, 0.30, 0.54, 0.78]
    for (label, val), x in zip(kpis, xs):
        fig.text(x, 0.42, _fmt(val), color=t["primary"],
                 fontsize=22, fontweight="bold")
        fig.text(x, 0.22, label, color=t["muted"], fontsize=9)

    fig.text(
        0.05, 0.06,
        f"{stats['ds_views']:,} dataset views · kaggle.com/{PROFILE}",
        color=t["muted"], fontsize=8,
    )

    out = ASSETS / f"kaggle_{theme}.png"
    fig.savefig(out, facecolor=t["bg"])
    plt.close(fig)
    print(f"wrote {out}")


def main() -> int:
    ASSETS.mkdir(exist_ok=True)
    stats = _fetch()
    print(f"stats: {stats}")
    for theme in THEMES:
        _render(stats, theme)
    return 0


if __name__ == "__main__":
    sys.exit(main())
