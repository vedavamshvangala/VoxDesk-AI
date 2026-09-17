"""Desktop window and UI inspection tools for AXE."""

from __future__ import annotations

from typing import Any

import win32gui
from pywinauto import Desktop


def get_open_windows() -> dict[str, Any]:
    """
    Return information about currently available desktop windows.
    """
    try:
        windows = Desktop(backend="uia").windows()
        results: list[dict[str, Any]] = []

        for window in windows:
            try:
                title = window.window_text().strip()

                if not title:
                    continue

                results.append(
                    {
                        "title": title,
                        "control_type": window.element_info.control_type,
                        "process_id": window.process_id(),
                    }
                )

            except Exception:
                continue

        return {
            "success": True,
            "count": len(results),
            "windows": results,
            "message": "Desktop windows inspected successfully.",
        }

    except Exception as exc:
        return {
            "success": False,
            "count": 0,
            "windows": [],
            "message": f"Failed to inspect desktop windows: {exc}",
        }


def get_active_window() -> dict[str, Any]:
    """
    Return information about the currently active foreground window.
    """
    try:
        hwnd = win32gui.GetForegroundWindow()

        if not hwnd:
            return {
                "success": False,
                "title": None,
                "control_type": None,
                "process_id": None,
                "message": "No active foreground window was found.",
            }

        desktop = Desktop(backend="uia")
        window = desktop.window(handle=hwnd)

        title = window.window_text().strip()
        control_type = window.element_info.control_type
        process_id = window.process_id()

        return {
            "success": True,
            "hwnd": hwnd,
            "title": title,
            "control_type": control_type,
            "process_id": process_id,
            "message": "Active window inspected successfully.",
        }

    except Exception as exc:
        return {
            "success": False,
            "title": None,
            "control_type": None,
            "process_id": None,
            "message": f"Failed to inspect active window: {exc}",
        }


def is_application_open(application: str) -> dict[str, Any]:
    """
    Determine whether an application has an open desktop window.

    Matching is performed against window titles using
    case-insensitive substring matching.
    """
    if not application or not application.strip():
        return {
            "success": False,
            "open": False,
            "application": application,
            "windows": [],
            "message": "Application name cannot be empty.",
        }

    application_name = application.strip().lower()

    try:
        windows = Desktop(backend="uia").windows()
        matches: list[dict[str, Any]] = []

        for window in windows:
            try:
                title = window.window_text().strip()

                if not title:
                    continue

                if application_name in title.lower():
                    matches.append(
                        {
                            "title": title,
                            "control_type": window.element_info.control_type,
                            "process_id": window.process_id(),
                        }
                    )

            except Exception:
                continue

        is_open = len(matches) > 0

        return {
            "success": True,
            "open": is_open,
            "application": application,
            "windows": matches,
            "message": (
                f"Application '{application}' is open."
                if is_open
                else f"Application '{application}' is not open."
            ),
        }

    except Exception as exc:
        return {
            "success": False,
            "open": False,
            "application": application,
            "windows": [],
            "message": f"Failed to inspect application '{application}': {exc}",
        }


def inspect_active_window_controls() -> dict[str, Any]:
    """
    Inspect the UI controls exposed by the currently active window.

    Returns basic UI Automation information without interacting
    with or modifying the controls.
    """
    try:
        hwnd = win32gui.GetForegroundWindow()

        if not hwnd:
            return {
                "success": False,
                "window": None,
                "controls": [],
                "count": 0,
                "message": "No active foreground window was found.",
            }

        desktop = Desktop(backend="uia")
        window = desktop.window(handle=hwnd)

        title = window.window_text().strip()
        process_id = window.process_id()

        controls: list[dict[str, Any]] = []

        for control in window.descendants():
            try:
                control_title = control.window_text().strip()
                control_type = control.element_info.control_type
                automation_id = control.element_info.automation_id

                controls.append(
                    {
                        "title": control_title,
                        "control_type": control_type,
                        "automation_id": automation_id,
                    }
                )

            except Exception:
                continue

        return {
            "success": True,
            "window": {
                "hwnd": hwnd,
                "title": title,
                "process_id": process_id,
            },
            "controls": controls,
            "count": len(controls),
            "message": "Active window controls inspected successfully.",
        }

    except Exception as exc:
        return {
            "success": False,
            "window": None,
            "controls": [],
            "count": 0,
            "message": f"Failed to inspect active window controls: {exc}",
        }


def get_active_text_control() -> dict[str, Any]:
    """
    Identify the active application's UI Automation text control.

    The Windows Notepad UI observed by AXE exposes its editor as a
    ``Document`` control. This function identifies that observed
    text-bearing control without modifying the UI.
    """
    try:
        hwnd = win32gui.GetForegroundWindow()

        if not hwnd:
            return {
                "success": False,
                "found": False,
                "control_type": None,
                "title": None,
                "automation_id": None,
                "message": "No active foreground window was found.",
            }

        desktop = Desktop(backend="uia")
        window = desktop.window(handle=hwnd)
        window_title = window.window_text().strip()
        process_id = window.process_id()

        for control in window.descendants():
            try:
                control_type = control.element_info.control_type

                if control_type != "Document":
                    continue

                title = control.window_text().strip()
                automation_id = control.element_info.automation_id

                return {
                    "success": True,
                    "found": True,
                    "hwnd": hwnd,
                    "window_title": window_title,
                    "process_id": process_id,
                    "control_type": control_type,
                    "title": title,
                    "automation_id": automation_id,
                    "message": "Active text control inspected successfully.",
                }

            except Exception:
                continue

        return {
            "success": True,
            "found": False,
            "hwnd": hwnd,
            "window_title": window_title,
            "process_id": process_id,
            "control_type": None,
            "title": None,
            "automation_id": None,
            "message": "No supported text control was found in the active window.",
        }

    except Exception as exc:
        return {
            "success": False,
            "found": False,
            "control_type": None,
            "title": None,
            "automation_id": None,
            "message": f"Failed to inspect active text control: {exc}",
        }


def get_active_text() -> dict[str, Any]:
    """
    Read the current text exposed by the active application's text control.

    This function is strictly read-only. It does not type, click,
    press keys, or otherwise modify the active application.
    """
    try:
        hwnd = win32gui.GetForegroundWindow()

        if not hwnd:
            return {
                "success": False,
                "found": False,
                "text": "",
                "window_title": None,
                "control_type": None,
                "message": "No active foreground window was found.",
            }

        desktop = Desktop(backend="uia")
        window = desktop.window(handle=hwnd)

        window_title = window.window_text().strip()
        process_id = window.process_id()

        text_control = None

        for control in window.descendants():
            try:
                control_type = control.element_info.control_type

                if control_type == "Document":
                    text_control = control
                    break

            except Exception:
                continue

        if text_control is None:
            return {
                "success": False,
                "found": False,
                "text": "",
                "hwnd": hwnd,
                "window_title": window_title,
                "process_id": process_id,
                "control_type": None,
                "message": "No supported text control was found in the active window.",
            }

        control_type = text_control.element_info.control_type
        title = text_control.window_text().strip()
        automation_id = text_control.element_info.automation_id

        try:
            text = text_control.window_text()
        except Exception as exc:
            return {
                "success": False,
                "found": True,
                "text": "",
                "hwnd": hwnd,
                "window_title": window_title,
                "process_id": process_id,
                "control_type": control_type,
                "title": title,
                "automation_id": automation_id,
                "message": f"Failed to read text from active text control: {exc}",
            }

        if text is None:
            return {
                "success": False,
                "found": True,
                "text": "",
                "hwnd": hwnd,
                "window_title": window_title,
                "process_id": process_id,
                "control_type": control_type,
                "title": title,
                "automation_id": automation_id,
                "message": "Active text control returned no readable text.",
            }

        return {
            "success": True,
            "found": True,
            "text": str(text),
            "hwnd": hwnd,
            "window_title": window_title,
            "process_id": process_id,
            "control_type": control_type,
            "title": title,
            "automation_id": automation_id,
            "message": "Active text read successfully.",
        }

    except Exception as exc:
        return {
            "success": False,
            "found": False,
            "text": "",
            "window_title": None,
            "control_type": None,
            "message": f"Failed to read active text: {exc}",
        }


def main() -> None:
    """Run desktop inspection from the command line."""
    result = get_open_windows()

    if not result["success"]:
        print(result["message"])
        return

    print(f"Found {result['count']} windows:\n")

    for window in result["windows"]:
        print(f"PID: {window['process_id']}")
        print(f"Title: {window['title']!r}")
        print(f"Control: {window['control_type']}")
        print("-" * 50)

    print("\nActive Window:")
    print(get_active_window())

    print("\nActive Window Controls:")
    controls = inspect_active_window_controls()

    if not controls["success"]:
        print(controls["message"])
        return

    print(f"Window: {controls['window']['title']!r}")
    print(f"Controls found: {controls['count']}\n")

    for control in controls["controls"]:
        print(
            f"Type: {control['control_type']!r} | "
            f"Title: {control['title']!r} | "
            f"Automation ID: {control['automation_id']!r}"
        )

    print("\nActive Text:")
    print(get_active_text())


if __name__ == "__main__":
    main()