"""Weekly updater: captures screenshots of Google Scholar and Kaggle profiles
and rewrites the README image references + "updated on" lines.

Each capture is best-effort: if one site blocks us (e.g. Google consent wall
or Kaggle layout change), we log the failure, keep the existing image, and
still update whatever succeeded.

Usage:
    python scripts/update_profiles.py
"""

from __future__ import annotations

import datetime as _dt
import pathlib
import re
import sys
import traceback

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

ROOT = pathlib.Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
README = ROOT / "README.md"

SCHOLAR_URL = (
    "https://scholar.google.com.au/citations?user=KxJU37kAAAAJ&hl=en"
)
KAGGLE_URL = "https://www.kaggle.com/enddl22"

SCHOLAR_IMG = ASSETS / "google_scholar_profile.png"
KAGGLE_IMG = ASSETS / "kg_profile.png"


def _dismiss_google_consent(page) -> None:
    """Click through Google's consent interstitial if it appears."""
    try:
        # The consent page redirects to consent.google.com.
        if "consent" in page.url:
            for label in ("I agree", "Accept all", "Alle akzeptieren"):
                btn = page.get_by_role("button", name=label)
                if btn.count():
                    btn.first.click()
                    page.wait_for_load_state("domcontentloaded")
                    break
    except Exception:
        pass


def _capture_scholar(page) -> bool:
    try:
        page.goto(SCHOLAR_URL, wait_until="domcontentloaded", timeout=60_000)
        _dismiss_google_consent(page)
        locator = page.locator("#gsc_rsb")
        locator.wait_for(state="visible", timeout=20_000)
        locator.screenshot(path=str(SCHOLAR_IMG))
        print("[scholar] captured")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"[scholar] skipped: {exc}")
        traceback.print_exc()
        return False


def _capture_kaggle(page) -> bool:
    try:
        page.set_viewport_size({"width": 1280, "height": 900})
        page.goto(KAGGLE_URL, wait_until="domcontentloaded", timeout=60_000)
        # Kaggle is an SPA; give it a beat to hydrate.
        try:
            page.wait_for_load_state("networkidle", timeout=15_000)
        except PWTimeout:
            pass
        page.wait_for_timeout(2_500)
        page.screenshot(
            path=str(KAGGLE_IMG),
            clip={"x": 0, "y": 0, "width": 1100, "height": 520},
        )
        print("[kaggle] captured")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"[kaggle] skipped: {exc}")
        traceback.print_exc()
        return False


def _update_readme(today: _dt.date) -> None:
    text = README.read_text()
    if sys.platform == "win32":
        human = today.strftime("%b/%#d/%Y")
    else:
        human = today.strftime("%b/%-d/%Y")

    text = re.sub(
        r"\./assets/google_scholar_profile[^\"\)\s]*\.png",
        "./assets/google_scholar_profile.png",
        text,
    )
    text = re.sub(
        r"\(updated on [^)]*\)",
        f"(updated on {human})",
        text,
        count=1,
    )
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
            locale="en-US",
        )
        page = context.new_page()
        scholar_ok = _capture_scholar(page)
        kaggle_ok = _capture_kaggle(page)
        browser.close()

    _update_readme(_dt.date.today())
    # Exit 0 even on partial failure; workflow will just commit what changed.
    print(f"done (scholar={scholar_ok}, kaggle={kaggle_ok})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
