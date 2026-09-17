"""AXE Windows desktop automation tools."""

import ctypes
import subprocess
import time

import psutil
import pyautogui
import win32com.client
from pywinauto import Desktop

import win32con
import win32gui
import win32process

from app.tools.applications import get_application


ALLOWED_KEYS = {
    "enter",
    "esc",
    "escape",
    "tab",
    "backspace",
    "delete",
    "space",
    "up",
    "down",
    "left",
    "right",
    "home",
    "end",
    "pageup",
    "pagedown",
    "insert",
    "shift",
    "ctrl",
    "alt",
    "win",
    "command",
    "capslock",
    "numlock",
    "scrolllock",
    "printscreen",
    "pause",
    "f1",
    "f2",
    "f3",
    "f4",
    "f5",
    "f6",
    "f7",
    "f8",
    "f9",
    "f10",
    "f11",
    "f12",
}


POWERSHELL_PATH = (
    r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
)


def _get_process_name(application: str) -> str | None:
    definition = get_application(application)

    if definition is None:
        return None

    return definition.process_name.lower()


def _get_window_process_names(application: str) -> tuple[str, ...]:
    definition = get_application(application)

    if definition is None:
        return ()

    if definition.window_process_names:
        return tuple(
            name.lower()
            for name in definition.window_process_names
        )

    return (definition.process_name.lower(),)


def _get_process_ids(process_name: str) -> list[int]:
    target = process_name.lower()
    process_ids = []

    for process in psutil.process_iter(["name"]):
        try:
            name = process.info["name"]

            if name and name.lower() == target:
                process_ids.append(process.pid)

        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
        ):
            continue

    return process_ids


def _process_exists(process_name: str) -> bool:
    return bool(_get_process_ids(process_name))


def _get_command_prompt_windows():
    """Return visible Command Prompt console windows as pywinauto windows."""

    matching_windows = []

    def collect_window(hwnd, _):
        try:
            if not win32gui.IsWindowVisible(hwnd):
                return

            _, process_id = win32process.GetWindowThreadProcessId(hwnd)

            if not process_id:
                return

            process_name = psutil.Process(process_id).name()

            if not process_name or process_name.lower() != "cmd.exe":
                return

            window = Desktop(
                backend="win32"
            ).window(handle=hwnd)

            if window.exists():
                matching_windows.append(window)

        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            RuntimeError,
        ):
            return
        except Exception:
            return

    try:
        win32gui.EnumWindows(collect_window, None)
    except Exception:
        return []

    return matching_windows


def _get_application_windows(application: str):
    definition = get_application(application)

    if definition is None:
        return []

    application_key = definition.name

    window_process_names = _get_window_process_names(
        application_key
    )

    if not window_process_names:
        return []

    matching_windows = []

    for window in Desktop(backend="uia").windows():
        try:
            if not window.is_visible():
                continue

            process_id = window.process_id()
            process = psutil.Process(process_id)
            process_name = process.name()

            if (
                process_name
                and process_name.lower()
                in window_process_names
            ):
                matching_windows.append(window)

        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            RuntimeError,
        ):
            continue

    if application_key == "command_prompt" and not matching_windows:
        return _get_command_prompt_windows()

    return matching_windows


def _get_explorer_shell_windows():
    """
    Return actual Windows File Explorer folder windows.

    Shell.Application.Windows() represents Explorer folder
    windows directly and avoids confusing the Windows desktop
    shell (Program Manager) or taskbar with File Explorer.
    """

    matching_windows = []

    try:
        shell = win32com.client.Dispatch(
            "Shell.Application"
        )

        for shell_window in shell.Windows():
            try:
                hwnd = int(shell_window.HWND)

                if not hwnd:
                    continue

                if not win32gui.IsWindowVisible(hwnd):
                    continue

                location_name = ""

                try:
                    location_name = (
                        shell_window.LocationName
                        or ""
                    ).strip()
                except Exception:
                    pass

                matching_windows.append(
                    {
                        "hwnd": hwnd,
                        "title": location_name,
                    }
                )

            except Exception:
                continue

    except Exception:
        return []

    return matching_windows


def _get_explorer_windows():
    """
    Return pywinauto windows corresponding to actual
    File Explorer folder windows.
    """

    shell_windows = _get_explorer_shell_windows()

    if not shell_windows:
        return []

    explorer_windows = []

    for shell_window in shell_windows:
        hwnd = shell_window["hwnd"]

        try:
            window = Desktop(
                backend="win32"
            ).window(
                handle=hwnd
            )

            if window.exists() and window.is_visible():
                explorer_windows.append(window)

        except Exception:
            continue

    return explorer_windows


def _get_foreground_window_info() -> dict:
    try:
        hwnd = win32gui.GetForegroundWindow()

        if not hwnd:
            return {
                "success": False,
                "hwnd": None,
                "title": None,
                "process_id": None,
                "process_name": None,
                "message": (
                    "No foreground window was detected."
                ),
            }

        title = win32gui.GetWindowText(hwnd)

        _, process_id = (
            win32process.GetWindowThreadProcessId(
                hwnd
            )
        )

        try:
            process_name = psutil.Process(
                process_id
            ).name()

        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
        ):
            process_name = None

        return {
            "success": True,
            "hwnd": hwnd,
            "title": title,
            "process_id": process_id,
            "process_name": process_name,
            "message": (
                "Foreground window detected successfully."
            ),
        }

    except Exception as exc:
        return {
            "success": False,
            "hwnd": None,
            "title": None,
            "process_id": None,
            "process_name": None,
            "message": (
                f"Failed to detect foreground window: {exc}"
            ),
        }


def _is_explorer_window(hwnd: int) -> bool:
    if not hwnd:
        return False

    for shell_window in _get_explorer_shell_windows():
        if shell_window["hwnd"] == hwnd:
            return True

    return False


def _get_foreground_explorer_window() -> int | None:
    try:
        hwnd = win32gui.GetForegroundWindow()

        if _is_explorer_window(hwnd):
            return hwnd

        return None

    except Exception:
        return None


def _find_explorer_window_from_shell_windows():
    windows = _get_explorer_windows()

    if not windows:
        return None

    return windows[0]


def _focus_window(window) -> bool:
    try:
        hwnd = window.handle

        if not hwnd or not win32gui.IsWindow(hwnd):
            return False

        try:
            window.set_focus()
        except Exception:
            pass

        try:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        except Exception:
            pass

        try:
            win32gui.BringWindowToTop(hwnd)
        except Exception:
            pass

        try:
            win32gui.SetForegroundWindow(hwnd)
        except Exception:
            pass

        time.sleep(0.3)

        if win32gui.GetForegroundWindow() == hwnd:
            return True

        # Windows may block SetForegroundWindow when the caller and target
        # belong to different input threads. Retry with temporary thread
        # input attachment only after the normal focus attempt fails.
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        foreground_hwnd = win32gui.GetForegroundWindow()

        if foreground_hwnd:
            foreground_thread, _ = win32process.GetWindowThreadProcessId(
                foreground_hwnd
            )
            current_thread = kernel32.GetCurrentThreadId()
            attached = False

            try:
                attached = bool(
                    user32.AttachThreadInput(
                        current_thread,
                        foreground_thread,
                        True,
                    )
                )

                win32gui.BringWindowToTop(hwnd)
                win32gui.SetForegroundWindow(hwnd)
                win32gui.SetActiveWindow(hwnd)
                time.sleep(0.3)
            finally:
                if attached:
                    user32.AttachThreadInput(
                        current_thread,
                        foreground_thread,
                        False,
                    )

        return win32gui.GetForegroundWindow() == hwnd

    except Exception:
        return False


def verify_application(application: str) -> bool:
    definition = get_application(application)

    if definition is None:
        return False

    application_key = definition.name

    if application_key == "file_explorer":
        return bool(
            _get_explorer_shell_windows()
        )

    if not _process_exists(
        definition.process_name
    ):
        return False

    return bool(
        _get_application_windows(application_key)
    )


def get_active_window() -> dict:
    return _get_foreground_window_info()


def get_window_info(application: str) -> dict:
    definition = get_application(application)

    if definition is None:
        return {
            "success": False,
            "application": application.strip().lower(),
            "title": None,
            "process_id": None,
            "visible": False,
            "message": (
                f"Application "
                f"'{application.strip().lower()}' "
                "is not supported."
            ),
        }

    application_key = definition.name

    if application_key == "file_explorer":
        shell_windows = (
            _get_explorer_shell_windows()
        )

        if not shell_windows:
            return {
                "success": False,
                "application": application_key,
                "title": None,
                "process_id": None,
                "visible": False,
                "message": (
                    "No actual File Explorer folder "
                    "window was found."
                ),
            }

        shell_window = shell_windows[0]
        hwnd = shell_window["hwnd"]

        try:
            _, process_id = (
                win32process.GetWindowThreadProcessId(
                    hwnd
                )
            )

            return {
                "success": True,
                "application": application_key,
                "title": (
                    win32gui.GetWindowText(hwnd)
                    or shell_window["title"]
                ),
                "process_id": process_id,
                "visible": bool(
                    win32gui.IsWindowVisible(hwnd)
                ),
                "message": (
                    "File Explorer window information "
                    "retrieved successfully."
                ),
            }

        except Exception as exc:
            return {
                "success": False,
                "application": application_key,
                "title": None,
                "process_id": None,
                "visible": False,
                "message": (
                    "Failed to retrieve File Explorer "
                    f"window information: {exc}"
                ),
            }

    windows = _get_application_windows(
        application_key
    )

    if not windows:
        return {
            "success": False,
            "application": application_key,
            "title": None,
            "process_id": None,
            "visible": False,
            "message": (
                f"No visible window found for "
                f"{application_key}."
            ),
        }

    try:
        window = windows[0]

        return {
            "success": True,
            "application": application_key,
            "title": window.window_text(),
            "process_id": window.process_id(),
            "visible": window.is_visible(),
            "message": (
                "Window information retrieved successfully."
            ),
        }

    except Exception as exc:
        return {
            "success": False,
            "application": application_key,
            "title": None,
            "process_id": None,
            "visible": False,
            "message": (
                f"Failed to retrieve window information: "
                f"{exc}"
            ),
        }


def verify_focus(application: str) -> dict:
    definition = get_application(application)

    if definition is None:
        return {
            "success": False,
            "application": application.strip().lower(),
            "focused": False,
            "message": (
                f"Application "
                f"'{application.strip().lower()}' "
                "is not supported."
            ),
        }

    application_key = definition.name
    active_result = get_active_window()

    if not active_result["success"]:
        return {
            "success": False,
            "application": application_key,
            "focused": False,
            "message": (
                "Could not determine the Windows "
                "foreground window."
            ),
        }

    active_process_name = (
        active_result["process_name"]
    )

    if application_key == "file_explorer":
        focused = (
            _get_foreground_explorer_window()
            is not None
        )

    else:
        allowed_window_process_names = set(
            _get_window_process_names(
                application_key
            )
        )

        focused = (
            active_process_name is not None
            and active_process_name.lower()
            in allowed_window_process_names
        )

    return {
        "success": True,
        "application": application_key,
        "focused": focused,
        "active_title": active_result["title"],
        "active_process_id": active_result[
            "process_id"
        ],
        "active_process_name": active_process_name,
        "message": (
            f"{application_key} is currently focused."
            if focused
            else (
                f"{application_key} is currently "
                "not focused."
            )
        ),
    }


def focus_application(application: str) -> dict:
    definition = get_application(application)

    if definition is None:
        return {
            "success": False,
            "application": application.strip().lower(),
            "message": (
                f"Application "
                f"'{application.strip().lower()}' "
                "is not supported."
            ),
        }

    application_key = definition.name

    if application_key == "file_explorer":
        window = (
            _find_explorer_window_from_shell_windows()
        )

    else:
        windows = _get_application_windows(
            application_key
        )

        window = windows[0] if windows else None

    if window is None:
        return {
            "success": False,
            "application": application_key,
            "message": (
                f"Could not find a visible "
                f"{application_key} window."
            ),
        }

    try:
        focused = _focus_window(window)

        if not focused:
            return {
                "success": False,
                "application": application_key,
                "message": (
                    f"Failed to focus "
                    f"{application_key}."
                ),
            }

        focus_result = verify_focus(
            application_key
        )

        if not focus_result["focused"]:
            return {
                "success": False,
                "application": application_key,
                "message": (
                    f"{application_key} received the "
                    "focus request, but Windows "
                    "foreground verification failed."
                ),
            }

        return {
            "success": True,
            "application": application_key,
            "message": (
                f"{application_key} focused successfully."
            ),
        }

    except Exception as exc:
        return {
            "success": False,
            "application": application_key,
            "message": (
                f"Failed to focus {application_key}: "
                f"{exc}"
            ),
        }


def _launch_application(definition) -> None:
    if definition.name == "command_prompt":
        subprocess.Popen(
            definition.executable,
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
        return

    if definition.launch_with_shell:
        subprocess.Popen(
            [
                POWERSHELL_PATH,
                "-NoProfile",
                "-Command",
                f"Start-Process {definition.executable}",
            ]
        )

        return

    subprocess.Popen(
        definition.executable
    )


def open_application(
    application: str,
    wait_seconds: float = 3.0,
) -> dict:
    definition = get_application(application)

    if definition is None:
        return {
            "success": False,
            "application": application.strip().lower(),
            "verified": False,
            "focused": False,
            "already_running": False,
            "message": (
                f"Application "
                f"'{application.strip().lower()}' "
                "is not supported."
            ),
        }

    application_key = definition.name

    if verify_application(application_key):
        focus_result = focus_application(
            application_key
        )

        if not focus_result["success"]:
            return {
                "success": False,
                "application": application_key,
                "verified": True,
                "focused": False,
                "already_running": True,
                "message": (
                    f"{application_key} is already open "
                    "and verified, but AXE could not "
                    "bring it to the foreground. "
                    f"{focus_result['message']}"
                ),
            }

        return {
            "success": True,
            "application": application_key,
            "verified": True,
            "focused": True,
            "already_running": True,
            "message": (
                f"{application_key} is already open, "
                "verified, and focused successfully."
            ),
        }

    try:
        _launch_application(definition)

        deadline = time.time() + wait_seconds

        while time.time() < deadline:
            if verify_application(
                application_key
            ):
                focus_result = focus_application(
                    application_key
                )

                if not focus_result["success"]:
                    return {
                        "success": False,
                        "application": application_key,
                        "verified": True,
                        "focused": False,
                        "already_running": False,
                        "message": (
                            f"{application_key} was "
                            "launched and verified, "
                            "but AXE could not bring "
                            "it to the foreground. "
                            f"{focus_result['message']}"
                        ),
                    }

                return {
                    "success": True,
                    "application": application_key,
                    "verified": True,
                    "focused": True,
                    "already_running": False,
                    "message": (
                        f"Successfully opened, "
                        f"verified, and focused "
                        f"{application_key}."
                    ),
                }

            time.sleep(0.1)

        return {
            "success": False,
            "application": application_key,
            "verified": False,
            "focused": False,
            "already_running": False,
            "message": (
                f"{application_key} was launched, but "
                "the application could not be verified."
            ),
        }

    except Exception as exc:
        return {
            "success": False,
            "application": application_key,
            "verified": False,
            "focused": False,
            "already_running": False,
            "message": (
                f"Failed to open {application_key}: "
                f"{exc}"
            ),
        }


def close_application(
    application: str,
    wait_seconds: float = 3.0,
) -> dict:
    """
    Gracefully close a supported application window.

    AXE sends a normal Windows close request to a visible
    window belonging to the requested application. It does
    not terminate the process forcibly.

    The caller/verifier is responsible for independently
    confirming that the application actually closed.
    """

    definition = get_application(application)

    if definition is None:
        return {
            "success": False,
            "application": application.strip().lower(),
            "requested": False,
            "message": (
                f"Application "
                f"'{application.strip().lower()}' "
                "is not supported."
            ),
        }

    application_key = definition.name

    if application_key == "file_explorer":
        windows = _get_explorer_windows()
    else:
        windows = _get_application_windows(
            application_key
        )

    if not windows:
        return {
            "success": False,
            "application": application_key,
            "requested": False,
            "message": (
                f"No visible {application_key} window "
                "was found to close."
            ),
        }

    close_requested = False
    closed_window_count = 0

    for window in windows:
        try:
            hwnd = window.handle

            if not hwnd:
                continue

            if not win32gui.IsWindow(hwnd):
                continue

            if not win32gui.IsWindowVisible(hwnd):
                continue

            win32gui.PostMessage(
                hwnd,
                win32con.WM_CLOSE,
                0,
                0,
            )

            close_requested = True
            closed_window_count += 1

        except Exception:
            continue

    if not close_requested:
        return {
            "success": False,
            "application": application_key,
            "requested": False,
            "message": (
                f"AXE could not send a close request "
                f"to {application_key}."
            ),
        }

    deadline = time.time() + wait_seconds

    while time.time() < deadline:
        if application_key == "file_explorer":
            still_open = bool(
                _get_explorer_shell_windows()
            )
        else:
            still_open = verify_application(
                application_key
            )

        if not still_open:
            return {
                "success": True,
                "application": application_key,
                "requested": True,
                "closed_window_count": closed_window_count,
                "verified_closed": True,
                "message": (
                    f"{application_key} close request was "
                    "sent and the application is no longer "
                    "detected."
                ),
            }

        time.sleep(0.1)

    return {
        "success": True,
        "application": application_key,
        "requested": True,
        "closed_window_count": closed_window_count,
        "verified_closed": False,
        "message": (
            f"Close request was sent to {application_key}, "
            "but the application is still detected. "
            "Independent verification is required."
        ),
    }


def type_text(text: str) -> dict:
    if not text:
        return {
            "success": False,
            "text": text,
            "message": "No text was provided.",
        }

    try:
        pyautogui.write(
            text,
            interval=0.03,
        )

        return {
            "success": True,
            "text": text,
            "message": "Text typed successfully.",
        }

    except Exception as exc:
        return {
            "success": False,
            "text": text,
            "message": (
                f"Failed to type text: {exc}"
            ),
        }


def press_key(key: str) -> dict:
    if not key:
        return {
            "success": False,
            "key": key,
            "message": "No key was provided.",
        }

    key_name = key.strip().lower()

    if key_name not in ALLOWED_KEYS:
        return {
            "success": False,
            "key": key_name,
            "message": (
                f"Key '{key_name}' is not allowed."
            ),
        }

    try:
        pyautogui.press(key_name)

        return {
            "success": True,
            "key": key_name,
            "message": (
                f"Key '{key_name}' pressed successfully."
            ),
        }

    except Exception as exc:
        return {
            "success": False,
            "key": key_name,
            "message": (
                f"Failed to press key '{key_name}': "
                f"{exc}"
            ),
        }


def hotkey(keys: list[str]) -> dict:
    """
    Execute a validated keyboard combination.

    AXE actions provide hotkey arguments in the form:

        {"keys": ["ctrl", "s"]}

    The function normalizes and validates those keys before
    passing them to PyAutoGUI.
    """

    if not isinstance(keys, list) or not keys:
        return {
            "success": False,
            "keys": [],
            "message": "No keys were provided.",
        }

    normalized_keys = [
        key.strip().lower()
        for key in keys
        if isinstance(key, str) and key.strip()
    ]

    if not normalized_keys:
        return {
            "success": False,
            "keys": [],
            "message": "No valid keys were provided.",
        }

    invalid_keys = [
        key
        for key in normalized_keys
        if key not in ALLOWED_KEYS and len(key) != 1
    ]

    if invalid_keys:
        return {
            "success": False,
            "keys": normalized_keys,
            "message": (
                f"Unsupported key(s): "
                f"{', '.join(invalid_keys)}."
            ),
        }

    try:
        pyautogui.hotkey(*normalized_keys)

        return {
            "success": True,
            "keys": normalized_keys,
            "message": (
                f"Hotkey '{'+'.join(normalized_keys)}' "
                "executed successfully."
            ),
        }

    except Exception as exc:
        return {
            "success": False,
            "keys": normalized_keys,
            "message": (
                f"Failed to execute hotkey: {exc}"
            ),
        }


