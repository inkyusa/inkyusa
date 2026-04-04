"""Weekly updater: captures a screenshot of the Kaggle profile and refreshes
the "as of ..." date in the README.

The Google Scholar image is served live by the vercel-citations API, so it
does not need a committed snapshot.

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

KAGGLE_URL = "https://www.kaggle.com/enddl22"
KAGGLE_IMG = ASSETS / "kg_profile.png"


def _capture_kaggle(page) -> bool:
    try:
        page.set_viewport_size({"width": 1280, "height": 900})
        page.goto(KAGGLE_URL, wait_until="domcontentloaded", timeout=60_000)
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
    new_text = re.sub(
        r"(as of )[A-Za-z]+/\d+/\d{4}",
        rf"\g<1>{human}",
        text,
        count=1,
    )
    if new_text != text:
        README.write_text(new_text)


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
        ok = _capture_kaggle(page)
        browser.close()

    _update_readme(_dt.date.today())
    print(f"done (kaggle={ok})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
