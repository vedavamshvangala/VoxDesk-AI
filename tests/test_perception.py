
from unittest.mock import Mock, patch

from app.tools.inspect_windows import (
    get_active_text,
    get_active_text_control,
    get_active_window,
    get_open_windows,
    inspect_active_window_controls,
    is_application_open,
)


def make_window():
    text_control = Mock()
    text_control.window_text.return_value = "Hello AXE"
    text_control.element_info.control_type = "Document"
    text_control.element_info.automation_id = ""

    button_control = Mock()
    button_control.window_text.return_value = "Close"
    button_control.element_info.control_type = "Button"
    button_control.element_info.automation_id = "CloseButton"

    window = Mock()
    window.window_text.return_value = "Hello AXE - Notepad"
    window.element_info.control_type = "Window"
    window.process_id.return_value = 4188
    window.descendants.return_value = [
        text_control,
        button_control,
    ]

    return window


def test_get_open_windows():
    window = make_window()

    with patch(
        "app.tools.inspect_windows.Desktop"
    ) as desktop_class:
        desktop_class.return_value.windows.return_value = [window]

        result = get_open_windows()

    assert result["success"] is True
    assert result["count"] == 1
    assert result["windows"] == [
        {
            "title": "Hello AXE - Notepad",
            "control_type": "Window",
            "process_id": 4188,
        }
    ]


def test_get_active_window():
    window = make_window()

    with patch(
        "app.tools.inspect_windows.win32gui.GetForegroundWindow",
        return_value=65902,
    ), patch(
        "app.tools.inspect_windows.Desktop"
    ) as desktop_class:
        desktop_class.return_value.window.return_value = window

        result = get_active_window()

    assert result["success"] is True
    assert result["hwnd"] == 65902
    assert result["title"] == "Hello AXE - Notepad"
    assert result["control_type"] == "Window"
    assert result["process_id"] == 4188


def test_is_application_open():
    window = make_window()

    with patch(
        "app.tools.inspect_windows.Desktop"
    ) as desktop_class:
        desktop_class.return_value.windows.return_value = [window]

        result = is_application_open("Notepad")

    assert result["success"] is True
    assert result["open"] is True
    assert result["windows"][0]["title"] == "Hello AXE - Notepad"


def test_inspect_active_window_controls():
    window = make_window()

    with patch(
        "app.tools.inspect_windows.win32gui.GetForegroundWindow",
        return_value=65902,
    ), patch(
        "app.tools.inspect_windows.Desktop"
    ) as desktop_class:
        desktop_class.return_value.window.return_value = window

        result = inspect_active_window_controls()

    assert result["success"] is True
    assert result["count"] == 2
    assert result["controls"][0] == {
        "title": "Hello AXE",
        "control_type": "Document",
        "automation_id": "",
    }


def test_get_active_text_control_returns_observed_document_control():
    window = make_window()

    with patch(
        "app.tools.inspect_windows.win32gui.GetForegroundWindow",
        return_value=65902,
    ), patch(
        "app.tools.inspect_windows.Desktop"
    ) as desktop_class:
        desktop_class.return_value.window.return_value = window

        result = get_active_text_control()

    assert result["success"] is True
    assert result["found"] is True
    assert result["hwnd"] == 65902
    assert result["process_id"] == 4188
    assert result["control_type"] == "Document"
    assert result["title"] == "Hello AXE"
    assert result["automation_id"] == ""


def test_get_active_text_control_reports_no_match_without_guessing():
    window = make_window()
    window.descendants.return_value = []

    with patch(
        "app.tools.inspect_windows.win32gui.GetForegroundWindow",
        return_value=65902,
    ), patch(
        "app.tools.inspect_windows.Desktop"
    ) as desktop_class:
        desktop_class.return_value.window.return_value = window

        result = get_active_text_control()

    assert result["success"] is True
    assert result["found"] is False
    assert result["control_type"] is None


def test_get_active_text_reads_document_text():
    window = make_window()

    with patch(
        "app.tools.inspect_windows.win32gui.GetForegroundWindow",
        return_value=65902,
    ), patch(
        "app.tools.inspect_windows.Desktop"
    ) as desktop_class:
        desktop_class.return_value.window.return_value = window

        result = get_active_text()

    assert result["success"] is True
    assert result["found"] is True
    assert result["text"] == "Hello AXE"
    assert result["hwnd"] == 65902
    assert result["window_title"] == "Hello AXE - Notepad"
    assert result["process_id"] == 4188
    assert result["control_type"] == "Document"
    assert result["title"] == "Hello AXE"
    assert result["automation_id"] == ""


def test_get_active_text_reports_no_active_window():
    with patch(
        "app.tools.inspect_windows.win32gui.GetForegroundWindow",
        return_value=0,
    ):
        result = get_active_text()

    assert result["success"] is False
    assert result["found"] is False
    assert result["text"] == ""
    assert result["window_title"] is None
    assert result["control_type"] is None


def test_get_active_text_reports_no_text_control():
    window = make_window()
    window.descendants.return_value = []

    with patch(
        "app.tools.inspect_windows.win32gui.GetForegroundWindow",
        return_value=65902,
    ), patch(
        "app.tools.inspect_windows.Desktop"
    ) as desktop_class:
        desktop_class.return_value.window.return_value = window

        result = get_active_text()

    assert result["success"] is False
    assert result["found"] is False
    assert result["text"] == ""
    assert result["control_type"] is None


def test_get_active_text_handles_text_read_failure():
    window = make_window()
    text_control = window.descendants.return_value[0]

    text_control.window_text.side_effect = [
        "Hello AXE",
        RuntimeError("UIA text retrieval failed"),
    ]

    with patch(
        "app.tools.inspect_windows.win32gui.GetForegroundWindow",
        return_value=65902,
    ), patch(
        "app.tools.inspect_windows.Desktop"
    ) as desktop_class:
        desktop_class.return_value.window.return_value = window

        result = get_active_text()

    assert result["success"] is False
    assert result["found"] is True
    assert result["text"] == ""
    assert result["control_type"] == "Document"
    assert "Failed to read text" in result["message"]

