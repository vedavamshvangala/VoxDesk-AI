from typing import Callable, Any

from app.tools.browser import (
    open_browser,
    navigate_browser,
    verify_browser,
    close_browser,
)

from app.tools.desktop import (
    open_application,
    focus_application,
    close_application,
    type_text,
    press_key,
    hotkey,
    verify_application,
)

from app.tools.calculator import calculator


def get_tool_registry() -> dict[str, Callable[..., Any]]:
    """
    Return the approved tools available to AXE.

    Only tools explicitly registered here can be executed
    by the TaskExecutor.
    """

    return {
        # Desktop tools
        "open_application": open_application,
        "focus_application": focus_application,
        "close_application": close_application,
        "type_text": type_text,
        "press_key": press_key,
        "hotkey": hotkey,
        "verify_application": verify_application,

        # Browser tools
        "open_browser": open_browser,
        "navigate_browser": navigate_browser,
        "verify_browser": verify_browser,
        "close_browser": close_browser,

        # Calculator tool
        "calculator": calculator,
    }