"""Weekly updater: captures screenshots of Google Scholar and Kaggle profiles
and rewrites the README image references + "updated on" lines.

Usage:
    python scripts/update_profiles.py
"""

from __future__ import annotations

import datetime as _dt
import pathlib
import re
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
README = ROOT / "README.md"

SCHOLAR_URL = (
    "https://scholar.google.com.au/citations?user=KxJU37kAAAAJ&hl=en"
)
KAGGLE_URL = "https://www.kaggle.com/enddl22"

SCHOLAR_IMG = ASSETS / "google_scholar_profile.png"
KAGGLE_IMG = ASSETS / "kg_profile.png"


def _capture_scholar(page) -> None:
    page.goto(SCHOLAR_URL, wait_until="networkidle", timeout=60_000)
    # The citations stats table on the right (contains totals + per-year bars).
    locator = page.locator("#gsc_rsb")
    locator.wait_for(state="visible", timeout=30_000)
    locator.screenshot(path=str(SCHOLAR_IMG))


def _capture_kaggle(page) -> None:
    page.goto(KAGGLE_URL, wait_until="networkidle", timeout=60_000)
    # Kaggle renders the profile header card at the top of the page. We clip
    # to a region that reliably contains the avatar + rank summary.
    page.set_viewport_size({"width": 1280, "height": 900})
    page.wait_for_timeout(2000)
    page.screenshot(
        path=str(KAGGLE_IMG),
        clip={"x": 0, "y": 0, "width": 1100, "height": 520},
    )


def _update_readme(today: _dt.date) -> None:
    text = README.read_text()
    human = today.strftime("%b/%-d/%Y") if sys.platform != "win32" else today.strftime("%b/%#d/%Y")

    # Point scholar image at the stable filename.
    text = re.sub(
        r"\./assets/google_scholar_profile[^\"\)\s]*\.png",
        "./assets/google_scholar_profile.png",
        text,
    )
    # Update the "updated on ..." line that follows the scholar image.
    text = re.sub(
        r"\(updated on [^)]*\)",
        f"(updated on {human})",
        text,
        count=1,
    )
    # Update the Kaggle "as of" date, preserving the ranking prefix.
    text = re.sub(
        r"(as of )[A-Za-z]+/\d+/\d{4}",
        rf"\g<1>{human}",
        text,
        count=1,
    )
    README.write_text(text)


def main() -> int:
    ASSETS.mkdir(exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0 Safari/537.36"
            ),
        )
        page = context.new_page()
        _capture_scholar(page)
        _capture_kaggle(page)
        browser.close()

    _update_readme(_dt.date.today())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
