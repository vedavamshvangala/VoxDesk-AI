from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from playwright.sync_api import Browser, Page, Playwright, sync_playwright


_playwright: Playwright | None = None
_browser: Browser | None = None
_page: Page | None = None


def _ensure_browser() -> Page:
    global _playwright
    global _browser
    global _page

    if _page is not None:
        try:
            _ = _page.url
            return _page
        except Exception:
            _page = None

    if _playwright is None:
        _playwright = sync_playwright().start()

    if _browser is None:
        _browser = _playwright.chromium.launch(
            headless=False
        )

    if _page is None:
        _page = _browser.new_page()

    return _page


def _normalize_url(url: str) -> str:
    url = url.strip()

    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    return url.rstrip("/")


def _normalize_hostname(url: str) -> str:
    hostname = (urlparse(url).hostname or "").lower()

    if hostname.startswith("www."):
        hostname = hostname[4:]

    return hostname


def focus_editable() -> dict[str, Any]:
    """Focus the first visible, enabled, editable element on the page."""

    page = _page

    if page is None:
        return {
            "success": False,
            "focused": False,
            "message": "No controlled browser page exists.",
        }

    try:
        candidates = page.locator(
            'input, textarea, [contenteditable="true"]'
        )

        for index in range(candidates.count()):
            candidate = candidates.nth(index)

            if not candidate.is_visible():
                continue

            if not candidate.is_enabled():
                continue

            if not candidate.is_editable():
                continue

            candidate.focus()
            focused = page.locator(":focus")

            if focused.count() != 1:
                continue

            same_element = candidate.evaluate(
                "element => element === document.activeElement"
            )

            if not same_element:
                continue

            tag = candidate.evaluate(
                "element => element.tagName.toLowerCase()"
            )

            return {
                "success": True,
                "focused": True,
                "tag": tag,
                "role": candidate.get_attribute("role"),
                "aria_label": candidate.get_attribute("aria-label"),
                "name": candidate.get_attribute("name"),
                "placeholder": candidate.get_attribute("placeholder"),
                "message": "A generic editable browser element was focused.",
            }

        return {
            "success": False,
            "focused": False,
            "message": "No visible, enabled, editable browser element was found.",
        }

    except Exception as exc:
        return {
            "success": False,
            "focused": False,
            "message": f"Browser editable focus failed: {exc}",
        }


def open_browser() -> dict[str, Any]:
    try:
        page = _ensure_browser()

        return {
            "success": True,
            "url": page.url,
            "message": "Browser opened successfully.",
        }

    except Exception as exc:
        return {
            "success": False,
            "url": None,
            "message": f"Failed to open browser: {exc}",
        }


def navigate_browser(url: str) -> dict[str, Any]:
    if not url or not url.strip():
        return {
            "success": False,
            "url": None,
            "message": "URL cannot be empty.",
        }

    normalized_url = _normalize_url(url)

    try:
        page = _ensure_browser()

        response = page.goto(
            normalized_url,
            wait_until="domcontentloaded",
            timeout=30000,
        )

        status_code = (
            response.status
            if response is not None
            else None
        )

        return {
            "success": True,
            "url": page.url,
            "status_code": status_code,
            "title": page.title(),
            "message": "Browser navigated successfully.",
        }

    except Exception as exc:
        return {
            "success": False,
            "url": normalized_url,
            "message": f"Failed to navigate browser: {exc}",
        }


def verify_browser(url: str | None = None) -> dict[str, Any]:
    try:
        page = _ensure_browser()
        current_url = page.url

        if not current_url:
            return {
                "success": False,
                "verified": False,
                "url": None,
                "message": "Browser has no active URL.",
            }

        if url:
            expected_url = _normalize_url(url)

            current_hostname = _normalize_hostname(
                current_url
            )

            expected_hostname = _normalize_hostname(
                expected_url
            )

            verified = (
                bool(current_hostname)
                and bool(expected_hostname)
                and current_hostname == expected_hostname
            )

            return {
                "success": verified,
                "verified": verified,
                "url": current_url,
                "expected_url": expected_url,
                "current_hostname": current_hostname,
                "expected_hostname": expected_hostname,
                "title": page.title(),
                "message": (
                    "Browser URL verified successfully."
                    if verified
                    else "Browser URL verification failed."
                ),
            }

        return {
            "success": True,
            "verified": True,
            "url": current_url,
            "title": page.title(),
            "message": "Browser is open and verified.",
        }

    except Exception as exc:
        return {
            "success": False,
            "verified": False,
            "url": None,
            "message": f"Browser verification failed: {exc}",
        }


def close_browser() -> dict[str, Any]:
    global _playwright
    global _browser
    global _page

    try:
        if _browser is not None:
            _browser.close()

        if _playwright is not None:
            _playwright.stop()

        _page = None
        _browser = None
        _playwright = None

        return {
            "success": True,
            "message": "Browser closed successfully.",
        }

    except Exception as exc:
        _page = None
        _browser = None
        _playwright = None

        return {
            "success": False,
            "message": f"Failed to close browser: {exc}",
        }