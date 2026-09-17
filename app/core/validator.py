
"""AXE task validation and safety layer."""

from typing import Any

from app.core.task import Action, Task
from app.tools.applications import get_application


class AXEValidator:
    """
    Validates structured AXE tasks before execution.

    The validator acts as a security boundary between the
    LLM planner and the execution runtime.

    The LLM can suggest actions, but only actions that pass
    validation are allowed to reach the executor.
    """

    ALLOWED_TOOLS = {
        # Desktop tools
        "open_application",
        "focus_application",
        "close_application",
        "type_text",
        "press_key",
        "hotkey",
        "verify_application",

        # Browser tools
        "open_browser",
        "navigate_browser",
        "verify_browser",
        "close_browser",

        # Calculator tool
        "calculator",
    }

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

    def validate_task(self, task: Task) -> dict[str, Any]:
        """
        Validate an entire AXE task.

        Returns a structured validation result.
        """

        if not isinstance(task, Task):
            return {
                "valid": False,
                "message": "Invalid AXE task.",
                "errors": [
                    "Task must be an instance of Task."
                ],
            }

        if not task.intent or not isinstance(task.intent, str):
            return {
                "valid": False,
                "message": "Task does not contain a valid intent.",
                "errors": [
                    "Task intent must be a non-empty string."
                ],
            }

        if not isinstance(task.actions, list):
            return {
                "valid": False,
                "message": "Task actions must be a list.",
                "errors": [
                    "Task actions must be stored in a list."
                ],
            }

        if not task.actions:
            return {
                "valid": False,
                "message": "Task contains no executable actions.",
                "errors": [
                    "At least one action is required."
                ],
            }

        errors: list[str] = []

        for index, action in enumerate(task.actions, start=1):
            action_errors = self.validate_action(action)

            for error in action_errors:
                errors.append(
                    f"Action {index}: {error}"
                )

        if errors:
            return {
                "valid": False,
                "message": "Task validation failed.",
                "errors": errors,
            }

        return {
            "valid": True,
            "message": "Task passed AXE validation.",
            "errors": [],
        }

    def validate_action(self, action: Action) -> list[str]:
        """
        Validate one AXE action.

        Returns a list of validation errors.
        An empty list means the action is valid.
        """

        errors: list[str] = []

        if not isinstance(action, Action):
            return [
                "Action must be an instance of Action."
            ]

        if not isinstance(action.tool, str):
            errors.append(
                "Tool name must be a string."
            )
            return errors

        tool = action.tool.strip()

        if not tool:
            errors.append(
                "Tool name cannot be empty."
            )
            return errors

        if tool not in self.ALLOWED_TOOLS:
            errors.append(
                f"Tool '{tool}' is not allowed."
            )
            return errors

        if not isinstance(action.arguments, dict):
            errors.append(
                f"Arguments for '{tool}' must be a dictionary."
            )
            return errors

        if tool in {
            "open_application",
            "focus_application",
            "close_application",
            "verify_application",
        }:
            errors.extend(
                self._validate_application_arguments(
                    tool,
                    action.arguments,
                )
            )

        elif tool == "type_text":
            errors.extend(
                self._validate_type_text_arguments(
                    action.arguments
                )
            )

        elif tool == "press_key":
            errors.extend(
                self._validate_press_key_arguments(
                    action.arguments
                )
            )

        elif tool == "hotkey":
            errors.extend(
                self._validate_hotkey_arguments(
                    action.arguments
                )
            )

        elif tool in {
            "open_browser",
            "close_browser",
        }:
            errors.extend(
                self._validate_browser_no_arguments(
                    tool,
                    action.arguments,
                )
            )

        elif tool == "navigate_browser":
            errors.extend(
                self._validate_navigate_browser_arguments(
                    action.arguments
                )
            )

        elif tool == "verify_browser":
            errors.extend(
                self._validate_verify_browser_arguments(
                    action.arguments
                )
            )

        elif tool == "calculator":
            errors.extend(
                self._validate_calculator_arguments(
                    action.arguments
                )
            )

        return errors

    def _validate_application_arguments(
        self,
        tool: str,
        arguments: dict[str, Any],
    ) -> list[str]:
        """
        Validate arguments for application-related tools.
        """

        errors: list[str] = []

        application = arguments.get("application")

        if not isinstance(application, str):
            errors.append(
                f"'{tool}' requires a string 'application' argument."
            )
            return errors

        application = application.strip().lower()

        if not application:
            errors.append(
                f"'{tool}' application cannot be empty."
            )
            return errors

        if get_application(application) is None:
            errors.append(
                f"Application '{application}' is not allowed."
            )

        return errors

    def _validate_type_text_arguments(
        self,
        arguments: dict[str, Any],
    ) -> list[str]:
        """
        Validate type_text arguments.
        """

        errors: list[str] = []

        text = arguments.get("text")

        if not isinstance(text, str):
            errors.append(
                "'type_text' requires a string 'text' argument."
            )
            return errors

        if not text:
            errors.append(
                "'type_text' cannot receive empty text."
            )

        return errors

    def _validate_press_key_arguments(
        self,
        arguments: dict[str, Any],
    ) -> list[str]:
        """
        Validate press_key arguments.
        """

        errors: list[str] = []

        key = arguments.get("key")

        if not isinstance(key, str):
            errors.append(
                "'press_key' requires a string 'key' argument."
            )
            return errors

        key = key.strip().lower()

        if not key:
            errors.append(
                "'press_key' key cannot be empty."
            )
            return errors

        if key not in self.ALLOWED_KEYS:
            errors.append(
                f"Key '{key}' is not allowed."
            )

        return errors

    def _validate_hotkey_arguments(
        self,
        arguments: dict[str, Any],
    ) -> list[str]:
        """
        Validate hotkey arguments.
        """

        errors: list[str] = []

        keys = arguments.get("keys")

        if not isinstance(keys, list):
            errors.append(
                "'hotkey' requires a list of 'keys'."
            )
            return errors

        if not keys:
            errors.append(
                "'hotkey' requires at least one key."
            )
            return errors

        for key in keys:
            if not isinstance(key, str):
                errors.append(
                    "Every hotkey value must be a string."
                )
                continue

            normalized_key = key.strip().lower()

            if not normalized_key:
                errors.append(
                    "Hotkey cannot contain an empty key."
                )
                continue

            if (
                normalized_key not in self.ALLOWED_KEYS
                and len(normalized_key) != 1
            ):
                errors.append(
                    f"Key '{normalized_key}' is not allowed."
                )

        return errors

    def _validate_browser_no_arguments(
        self,
        tool: str,
        arguments: dict[str, Any],
    ) -> list[str]:
        """
        Validate browser tools that do not require arguments.

        open_browser and close_browser do not require
        any arguments.
        """

        # These tools intentionally require no arguments.
        # We do not reject additional arguments here because
        # the executor only receives controlled tool calls and
        # the actual browser functions do not accept arbitrary
        # parameters.
        return []

    def _validate_navigate_browser_arguments(
        self,
        arguments: dict[str, Any],
    ) -> list[str]:
        """
        Validate navigate_browser arguments.
        """

        errors: list[str] = []

        url = arguments.get("url")

        if not isinstance(url, str):
            errors.append(
                "'navigate_browser' requires a string 'url' argument."
            )
            return errors

        url = url.strip()

        if not url:
            errors.append(
                "'navigate_browser' URL cannot be empty."
            )
            return errors

        if not url.startswith(
            ("http://", "https://")
        ):
            # The browser tool intentionally accepts domains such
            # as example.com and normalizes them to HTTPS.
            if " " in url:
                errors.append(
                    "'navigate_browser' URL cannot contain spaces."
                )

        return errors

    def _validate_verify_browser_arguments(
        self,
        arguments: dict[str, Any],
    ) -> list[str]:
        """
        Validate verify_browser arguments.

        The URL is optional because verify_browser can also
        simply verify that the controlled browser is open.
        """

        errors: list[str] = []

        if "url" not in arguments:
            return errors

        url = arguments.get("url")

        if not isinstance(url, str):
            errors.append(
                "'verify_browser' 'url' must be a string."
            )
            return errors

        url = url.strip()

        if not url:
            errors.append(
                "'verify_browser' URL cannot be empty."
            )
            return errors

        if not url.startswith(
            ("http://", "https://")
        ):
            if " " in url:
                errors.append(
                    "'verify_browser' URL cannot contain spaces."
                )

        return errors

    def _validate_calculator_arguments(
        self,
        arguments: dict[str, Any],
    ) -> list[str]:
        """
        Validate calculator arguments.

        The calculator requires one argument:

            expression: str

        The calculator tool itself is responsible for safely
        parsing and evaluating the arithmetic expression.
        """

        errors: list[str] = []

        expression = arguments.get("expression")

        if not isinstance(expression, str):
            errors.append(
                "'calculator' requires a string 'expression' argument."
            )
            return errors

        expression = expression.strip()

        if not expression:
            errors.append(
                "'calculator' expression cannot be empty."
            )

        return errors

