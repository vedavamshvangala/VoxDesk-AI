"""Controlled Windows application registry for AXE."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ApplicationDefinition:
    name: str
    executable: str
    process_name: str
    window_process_names: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()
    launch_with_shell: bool = False


APPLICATIONS = {
    "notepad": ApplicationDefinition(
        name="notepad",
        executable="notepad.exe",
        process_name="Notepad.exe",
        window_process_names=("Notepad.exe",),
        aliases=("note pad",),
    ),
    "calculator": ApplicationDefinition(
        name="calculator",
        executable="calc.exe",
        process_name="CalculatorApp.exe",
        window_process_names=("ApplicationFrameHost.exe",),
        aliases=("calc",),
    ),
    "file_explorer": ApplicationDefinition(
        name="file_explorer",
        executable="explorer.exe",
        process_name="explorer.exe",
        window_process_names=("explorer.exe",),
        aliases=(
            "file explorer",
            "explorer",
            "windows explorer",
        ),
    ),
    "paint": ApplicationDefinition(
        name="paint",
        executable="mspaint.exe",
        process_name="mspaint.exe",
        window_process_names=("mspaint.exe",),
        aliases=(
            "ms paint",
            "microsoft paint",
        ),
        launch_with_shell=True,
    ),
    "command_prompt": ApplicationDefinition(
        name="command_prompt",
        executable="cmd.exe",
        process_name="cmd.exe",
        window_process_names=("cmd.exe",),
        aliases=(
            "command prompt",
            "cmd",
            "command line",
        ),
    ),
    "vscode": ApplicationDefinition(
        name="vscode",
        executable="code",
        process_name="Code.exe",
        window_process_names=("Code.exe",),
        aliases=(
            "vs code",
            "visual studio code",
            "visual studio",
        ),
        launch_with_shell=True,
    ),
}


def normalize_application_name(application: str) -> str:
    normalized = application.strip().lower()

    if not normalized:
        return ""

    if normalized in APPLICATIONS:
        return normalized

    for name, definition in APPLICATIONS.items():
        if normalized in definition.aliases:
            return name

    return normalized


def get_application(application: str):
    canonical_name = normalize_application_name(application)
    return APPLICATIONS.get(canonical_name)


def is_application_allowed(application: str) -> bool:
    return get_application(application) is not None


def get_allowed_applications() -> list[str]:
    return list(APPLICATIONS.keys())