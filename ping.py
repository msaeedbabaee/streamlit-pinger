"""
Keep Streamlit Community Cloud apps awake.

WHY THIS ISN'T A PLAIN requests.get() SCRIPT ANYMORE
------------------------------------------------------
A sleeping Streamlit Community Cloud app still answers a plain HTTP GET with
"200 OK" — but that response is a small static HTML shell (a few KB) that
just tells a *browser* to open a WebSocket and start the actual app. Your
Python process never does that handshake, so the app script never runs and
the "last active" timer never resets. That's why the old requests.get()
version logged [SUCCESS] on every run while the apps kept sleeping.

This version drives a real (headless) browser with Playwright, so it:
  1. Loads the page like a visitor would.
  2. Clicks the "Yes, get this app back up!" button if the app is asleep.
  3. Waits for Streamlit's own app container to actually render, and retries
     with a page reload a few times if the app is still cold-starting.

Exit code is 0 even if some apps couldn't be confirmed awake (cold starts can
legitimately take a couple of minutes) — check the printed summary instead
of relying on the exit code to page you.
"""

import sys
import time

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

URLS_FILE = "urls.txt"

# Selector for Streamlit's own app root — only present once the app has
# actually started, not just when the static shell has loaded.
APP_CONTAINER_SELECTOR = "div[data-testid='stAppViewContainer']"

# Exact text Streamlit Community Cloud uses on the sleep screen's button.
WAKE_BUTTON_TEXT = "Yes, get this app back up"

PAGE_LOAD_TIMEOUT_MS = 45_000       # generous: cold Community Cloud hosts can be slow to answer
APP_READY_TIMEOUT_MS = 20_000       # how long to wait for the app container per attempt
MAX_WAKE_ATTEMPTS = 6               # reload-and-retry loop for slow cold starts
WAIT_BETWEEN_ATTEMPTS_S = 15


def load_urls(path: str = URLS_FILE) -> list[str]:
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


def click_wake_button_if_present(page) -> bool:
    """Click the sleep screen's wake-up button if it's showing. Returns True if clicked."""
    try:
        button = page.get_by_role("button", name=WAKE_BUTTON_TEXT)
        if button.is_visible(timeout=3_000):
            button.click()
            return True
    except PlaywrightTimeoutError:
        pass
    except Exception:
        pass
    return False


def wait_for_app_ready(page, timeout_ms: int = APP_READY_TIMEOUT_MS) -> bool:
    try:
        page.wait_for_selector(APP_CONTAINER_SELECTOR, timeout=timeout_ms, state="attached")
        return True
    except PlaywrightTimeoutError:
        return False


def visit(page, url: str) -> bool:
    page.goto(url, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT_MS)

    if wait_for_app_ready(page, timeout_ms=8_000):
        print("  [AWAKE] app was already running")
        return True

    clicked = click_wake_button_if_present(page)
    print("  [ASLEEP] wake-up button clicked" if clicked else "  [LOADING] no wake button seen yet, waiting for app to start")

    for attempt in range(1, MAX_WAKE_ATTEMPTS + 1):
        if wait_for_app_ready(page):
            print(f"  [WOKEN] app rendered after {attempt} check(s)")
            return True
        print(f"  ...still starting (attempt {attempt}/{MAX_WAKE_ATTEMPTS}), reloading")
        time.sleep(WAIT_BETWEEN_ATTEMPTS_S)
        try:
            page.reload(wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT_MS)
        except PlaywrightTimeoutError:
            continue
        click_wake_button_if_present(page)

    return False


def main() -> int:
    urls = load_urls()
    print(f"Total apps to ping: {len(urls)}")

    failures: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})

        for url in urls:
            print(f"\nVisiting: {url}")
            try:
                if not visit(page, url):
                    print("  [TIMEOUT] app never confirmed awake within the retry budget")
                    failures.append(url)
            except Exception as e:
                print(f"  [FAILED] {url}: {e}")
                failures.append(url)

        browser.close()

    print("\n" + "=" * 60)
    if failures:
        print(f"{len(failures)} of {len(urls)} app(s) could not be confirmed awake:")
        for u in failures:
            print(f"  - {u}")
        print(
            "\nThis can happen on a very cold start (first request after days idle) — "
            "the next scheduled run will likely catch it. If a specific app fails "
            "every run, open it manually once in a browser to check it isn't broken."
        )
    else:
        print(f"All {len(urls)} app(s) confirmed awake.")

    # Non-zero exit is deliberately NOT used here: a slow cold start is expected
    # behaviour, not a workflow failure, and would just create noisy red X's in Actions.
    return 0


if __name__ == "__main__":
    sys.exit(main())
