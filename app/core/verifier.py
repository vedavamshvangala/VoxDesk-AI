from typing import Any
from urllib.parse import urlparse

from app.core.task import Action
from app.tools.desktop import (
_get_application_windows,
_get_explorer_shell_windows,
verify_application,
verify_focus,
)
from app.tools import browser
from app.tools.calculator import calculator

class AXEVerifier:
    def verify_action(
        self,
        action: Action,
        execution_result: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(action, Action):
            return self._not_verified(
                method="invalid_action",
                message="Verification failed because the supplied action is invalid.",
            )

        if not isinstance(execution_result, dict):
            return self._not_verified(
                method="invalid_execution_result",
                message="Verification failed because the execution result is invalid.",
            )

        tool = action.tool

        if tool == "open_application":
            return self._verify_open_application(action)

        if tool == "focus_application":
            return self._verify_focus_application(action)

        if tool == "close_application":
            return self._verify_close_application(
                action,
                execution_result,
            )

        if tool == "verify_application":
            return self._verify_application(action)

        if tool == "type_text":
            return self._verify_type_text(
                action,
                execution_result,
            )

        if tool == "press_key":
            return self._verify_press_key(
                action,
                execution_result,
            )

        if tool == "hotkey":
            return self._verify_hotkey(
                action,
                execution_result,
            )

        if tool == "open_browser":
            return self._verify_open_browser(
                action,
                execution_result,
            )

        if tool == "navigate_browser":
            return self._verify_navigate_browser(
                action,
                execution_result,
            )

        if tool == "verify_browser":
            return self._verify_browser(
                action,
                execution_result,
            )

        if tool == "close_browser":
            return self._verify_close_browser(
                action,
                execution_result,
            )

        if tool == "calculator":
            return self._verify_calculator(
                action,
                execution_result,
            )

        return self._not_verified(
            method="unsupported_tool",
            message=(
                f"Independent verification is not implemented "
                f"for tool '{tool}'."
            ),
        )

    def _verify_calculator(
        self,
        action: Action,
        execution_result: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Independently verify a calculator action.

        Calculator operations are deterministic, so verification
        recomputes the expression and compares the independently
        obtained result with the executor result.
        """

        expression = action.arguments.get("expression")

        if not isinstance(expression, str) or not expression.strip():
            return self._not_verified(
                method="calculator_missing_expression",
                evidence={
                    "expression": expression,
                },
                message="Cannot verify calculator action because no expression was provided.",
            )

        if not execution_result.get("success"):
            return self._not_verified(
                method="calculator_execution_failed",
                evidence={
                    "expression": expression,
                    "execution_result": execution_result,
                },
                message="Calculator action did not execute successfully.",
            )

        try:
            independent_result = calculator(expression=expression)
        except Exception as exc:
            return self._not_verified(
                method="calculator_verification_error",
                evidence={
                    "expression": expression,
                    "error": str(exc),
                },
                message=f"An error occurred while independently verifying the calculation: {exc}",
            )

        if not isinstance(independent_result, dict):
            return self._not_verified(
                method="calculator_invalid_verification_result",
                evidence={
                    "expression": expression,
                    "independent_result": independent_result,
                },
                message="The independent calculator verification returned an invalid result.",
            )

        if not independent_result.get("success"):
            return self._not_verified(
                method="calculator_recalculation_failed",
                evidence={
                    "expression": expression,
                    "independent_result": independent_result,
                },
                message=(
                    "The calculator action executed, but the expression "
                    "could not be independently recalculated."
                ),
            )

        expected_result = independent_result.get("result")

        # The runtime wraps the calculator tool response inside its
        # top-level "result" field. Extract the actual calculator result
        # before comparing it with the independently recalculated value.
        runtime_result = execution_result.get("result")
        if isinstance(runtime_result, dict) and "result" in runtime_result:
            actual_result = runtime_result.get("result")
        else:
            actual_result = runtime_result

        if expected_result != actual_result:
            return self._not_verified(
                method="calculator_result_mismatch",
                evidence={
                    "expression": expression,
                    "expected_result": expected_result,
                    "actual_result": actual_result,
                    "result_match": False,
                },
                message=(
                    "Calculator execution completed, but the returned result "
                    "did not match the independently recalculated result."
                ),
            )

        return {
            "verified": True,
            "method": "calculator_result_recalculation",
            "evidence": {
                "expression": expression,
                "expected_result": expected_result,
                "actual_result": actual_result,
                "result_match": True,
            },
            "message": (
                "Calculator execution was independently verified by "
                "recalculating the expression and matching the result."
            ),
        }

    def _verify_open_application(
        self,
        action: Action,
    ) -> dict[str, Any]:
        application = action.arguments.get("application")

        if not application:
            return self._not_verified(
                method="open_application_missing_application",
                message="Cannot verify application opening because no application was provided.",
            )

        application_result = verify_application(application)

        if not application_result:
            return self._not_verified(
                method="application_not_open",
                evidence={
                    "application": application,
                    "application_verification": application_result,
                },
                message=(
                    f"Application '{application}' could not be "
                    "independently verified as open."
                ),
            )

        focus_result = verify_focus(application)

        if (
            not focus_result.get("success")
            or not focus_result.get("focused")
        ):
            return self._not_verified(
                method="application_not_focused",
                evidence={
                    "application": application,
                    "application_verification": application_result,
                    "focus_verification": focus_result,
                },
                message=(
                    f"Application '{application}' is open, but "
                    "its focus could not be independently verified."
                ),
            )

        return {
            "verified": True,
            "method": "application_open_and_focused",
            "evidence": {
                "application": application,
                "application_open": True,
                "application_focused": True,
            },
            "message": (
                f"Application '{application}' was independently "
                "verified as open and focused."
            ),
        }

    def _verify_focus_application(
        self,
        action: Action,
    ) -> dict[str, Any]:
        application = action.arguments.get("application")

        if not application:
            return self._not_verified(
                method="focus_application_missing_application",
                message="Cannot verify application focus because no application was provided.",
            )

        result = verify_focus(application)

        if (
            not result.get("success")
            or not result.get("focused")
        ):
            return self._not_verified(
                method="application_not_focused",
                evidence={
                    "application": application,
                    "focus_verification": result,
                },
                message=(
                    f"Application '{application}' could not be "
                    "independently verified as focused."
                ),
            )

        return {
            "verified": True,
            "method": "application_focus",
            "evidence": {
                "application": application,
                "focused": True,
            },
            "message": (
                f"Application '{application}' was independently "
                "verified as focused."
            ),
        }

    def _verify_close_application(
        self,
        action: Action,
        execution_result: dict[str, Any],
    ) -> dict[str, Any]:
        application = action.arguments.get("application")

        if not application:
            return self._not_verified(
                method="close_application_missing_application",
                message="Cannot verify application close because no application was provided.",
            )

        if not execution_result.get("success"):
            return self._not_verified(
                method="close_execution_failed",
                evidence={
                    "application": application,
                    "execution_result": execution_result,
                },
                message=(
                    f"Close action for '{application}' did not "
                    "execute successfully."
                ),
            )

        try:
            if application == "file_explorer":
                windows = _get_explorer_shell_windows()
            else:
                windows = _get_application_windows(application)
        except Exception as exc:
            return self._not_verified(
                method="close_verification_error",
                evidence={
                    "application": application,
                    "error": str(exc),
                },
                message=(
                    f"Unable to independently verify that "
                    f"'{application}' closed: {exc}"
                ),
            )

        if windows:
            return self._not_verified(
                method="application_still_open",
                evidence={
                    "application": application,
                    "remaining_windows": windows,
                },
                message=(
                    f"Application '{application}' is still "
                    "observable after the close action."
                ),
            )

        return {
            "verified": True,
            "method": "application_closed",
            "evidence": {
                "application": application,
                "application_open": False,
                "remaining_windows": [],
            },
            "message": (
                f"Application '{application}' was independently "
                "verified as closed."
            ),
        }

    def _verify_application(
        self,
        action: Action,
    ) -> dict[str, Any]:
        application = action.arguments.get("application")

        if not application:
            return self._not_verified(
                method="verify_application_missing_application",
                message="Cannot verify application because no application was provided.",
            )

        result = verify_application(application)

        if not result:
            return self._not_verified(
                method="application_verification_failed",
                evidence={
                    "application": application,
                    "verification": result,
                },
                message=(
                    f"Application '{application}' could not "
                    "be independently verified."
                ),
            )

        return {
            "verified": True,
            "method": "application_presence",
            "evidence": {
                "application": application,
                "application_open": True,
            },
            "message": (
                f"Application '{application}' was independently "
                "verified as available."
            ),
        }

    def _get_browser_page(self) -> Any | None:
        page = getattr(browser, "_page", None)

        if page is None:
            return None

        try:
            _ = page.url
            return page
        except Exception:
            return None

    def _normalize_browser_url(
        self,
        url: str,
    ) -> str:
        normalized = url.strip()

        if not normalized.startswith(("http://", "https://")):
            normalized = f"https://{normalized}"

        return normalized.rstrip("/")

    def _normalize_browser_hostname(
        self,
        url: str,
    ) -> str:
        normalized = self._normalize_browser_url(url)
        hostname = (urlparse(normalized).hostname or "").lower()

        if hostname.startswith("www."):
            hostname = hostname[4:]

        return hostname

    def _verify_open_browser(
        self,
        action: Action,
        execution_result: dict[str, Any],
    ) -> dict[str, Any]:
        if not execution_result.get("success"):
            return self._not_verified(
                method="browser_open_execution_failed",
                evidence={
                    "execution_result": execution_result,
                },
                message="Browser open action did not execute successfully.",
            )

        page = self._get_browser_page()

        if page is None:
            return self._not_verified(
                method="browser_not_open",
                evidence={
                    "execution_result": execution_result,
                    "browser_page_exists": False,
                },
                message=(
                    "The controlled browser could not be "
                    "independently verified as open."
                ),
            )

        try:
            current_url = page.url
            title = page.title()
        except Exception as exc:
            return self._not_verified(
                method="browser_state_unavailable",
                evidence={
                    "error": str(exc),
                },
                message=(
                    "The controlled browser exists, but its "
                    f"observable state could not be read: {exc}"
                ),
            )

        return {
            "verified": True,
            "method": "browser_open",
            "evidence": {
                "browser_open": True,
                "page_exists": True,
                "url": current_url,
                "title": title,
            },
            "message": (
                "The controlled browser was independently "
                "verified as open."
            ),
        }

    def _verify_navigate_browser(
        self,
        action: Action,
        execution_result: dict[str, Any],
    ) -> dict[str, Any]:
        expected_url = action.arguments.get("url")

        if not isinstance(expected_url, str) or not expected_url.strip():
            return self._not_verified(
                method="browser_navigation_missing_url",
                message=(
                    "Cannot verify browser navigation because "
                    "no expected URL was provided."
                ),
            )

        if not execution_result.get("success"):
            return self._not_verified(
                method="browser_navigation_execution_failed",
                evidence={
                    "expected_url": expected_url,
                    "execution_result": execution_result,
                },
                message="Browser navigation did not execute successfully.",
            )

        page = self._get_browser_page()

        if page is None:
            return self._not_verified(
                method="browser_not_open",
                evidence={
                    "expected_url": expected_url,
                    "browser_page_exists": False,
                },
                message=(
                    "The controlled browser could not be found "
                    "while verifying navigation."
                ),
            )

        try:
            actual_url = page.url
            title = page.title()
        except Exception as exc:
            return self._not_verified(
                method="browser_navigation_state_unavailable",
                evidence={
                    "expected_url": expected_url,
                    "error": str(exc),
                },
                message=(
                    "The browser URL could not be independently "
                    f"read: {exc}"
                ),
            )

        expected_hostname = self._normalize_browser_hostname(expected_url)
        actual_hostname = self._normalize_browser_hostname(actual_url)

        hostname_match = (
            bool(expected_hostname)
            and bool(actual_hostname)
            and expected_hostname == actual_hostname
        )

        if not hostname_match:
            return self._not_verified(
                method="browser_hostname_mismatch",
                evidence={
                    "expected_url": expected_url,
                    "actual_url": actual_url,
                    "expected_hostname": expected_hostname,
                    "actual_hostname": actual_hostname,
                    "hostname_match": False,
                    "title": title,
                },
                message=(
                    "Browser navigation executed, but the actual "
                    "browser hostname does not match the requested site."
                ),
            )

        return {
            "verified": True,
            "method": "browser_hostname_navigation",
            "evidence": {
                "expected_url": expected_url,
                "actual_url": actual_url,
                "expected_hostname": expected_hostname,
                "actual_hostname": actual_hostname,
                "hostname_match": True,
                "title": title,
            },
            "message": (
                "Browser navigation was independently verified "
                "by reading the actual browser hostname."
            ),
        }

    def _verify_browser(
        self,
        action: Action,
        execution_result: dict[str, Any],
    ) -> dict[str, Any]:
        if not execution_result.get("success"):
            return self._not_verified(
                method="browser_verification_execution_failed",
                evidence={
                    "execution_result": execution_result,
                },
                message=(
                    "Browser verification action did not "
                    "execute successfully."
                ),
            )

        page = self._get_browser_page()

        if page is None:
            return self._not_verified(
                method="browser_not_open",
                evidence={
                    "browser_page_exists": False,
                },
                message=(
                    "The controlled browser could not be "
                    "independently verified as open."
                ),
            )

        try:
            actual_url = page.url
            title = page.title()
        except Exception as exc:
            return self._not_verified(
                method="browser_state_unavailable",
                evidence={
                    "error": str(exc),
                },
                message=(
                    "The controlled browser state could not "
                    f"be read: {exc}"
                ),
            )

        expected_url = action.arguments.get("url")

        if isinstance(expected_url, str) and expected_url.strip():
            expected_hostname = self._normalize_browser_hostname(expected_url)
            actual_hostname = self._normalize_browser_hostname(actual_url)

            hostname_match = (
                bool(expected_hostname)
                and bool(actual_hostname)
                and expected_hostname == actual_hostname
            )

            if not hostname_match:
                return self._not_verified(
                    method="browser_verification_hostname_mismatch",
                    evidence={
                        "expected_url": expected_url,
                        "actual_url": actual_url,
                        "expected_hostname": expected_hostname,
                        "actual_hostname": actual_hostname,
                        "hostname_match": False,
                        "title": title,
                    },
                    message=(
                        "Browser is open, but its current hostname "
                        "does not match the expected site."
                    ),
                )

            return {
                "verified": True,
                "method": "browser_open_and_hostname",
                "evidence": {
                    "browser_open": True,
                    "page_exists": True,
                    "expected_url": expected_url,
                    "actual_url": actual_url,
                    "expected_hostname": expected_hostname,
                    "actual_hostname": actual_hostname,
                    "hostname_match": True,
                    "title": title,
                },
                "message": (
                    "The controlled browser and its current "
                    "hostname were independently verified."
                ),
            }

        return {
            "verified": True,
            "method": "browser_presence",
            "evidence": {
                "browser_open": True,
                "page_exists": True,
                "url": actual_url,
                "title": title,
            },
            "message": (
                "The controlled browser was independently "
                "verified as open."
            ),
        }

    def _verify_close_browser(
        self,
        action: Action,
        execution_result: dict[str, Any],
    ) -> dict[str, Any]:
        if not execution_result.get("success"):
            return self._not_verified(
                method="browser_close_execution_failed",
                evidence={
                    "execution_result": execution_result,
                },
                message="Browser close action did not execute successfully.",
            )

        page = getattr(browser, "_page", None)
        active_browser = getattr(browser, "_browser", None)

        if page is not None or active_browser is not None:
            return self._not_verified(
                method="browser_still_open",
                evidence={
                    "page_exists": page is not None,
                    "browser_exists": active_browser is not None,
                },
                message=(
                    "The controlled browser still appears to "
                    "have an active Playwright session."
                ),
            )

        return {
            "verified": True,
            "method": "browser_closed",
            "evidence": {
                "browser_open": False,
                "page_exists": False,
                "browser_exists": False,
            },
            "message": (
                "The controlled browser was independently "
                "verified as closed."
            ),
        }

    def _verify_type_text(
        self,
        action: Action,
        execution_result: dict[str, Any],
    ) -> dict[str, Any]:
        expected_text = action.arguments.get("text")

        if not expected_text:
            return self._not_verified(
                method="type_text_missing_text",
                message="Cannot verify text typing because no expected text was provided.",
            )

        application = execution_result.get("application")

        if not application:
            application = action.arguments.get("application")

        if application == "browser" or execution_result.get("browser_open"):
            return self._verify_browser_type_text(
                action,
                execution_result,
            )

        if not application:
            return self._not_verified(
                method="type_text_missing_application",
                message="Cannot verify typed text because the target application is unknown.",
            )

        if application != "notepad":
            return self._not_verified(
                method="type_text_application_unsupported",
                evidence={
                    "application": application,
                    "expected_text": expected_text,
                },
                message=(
                    "Independent text verification is currently "
                    f"implemented only for Notepad, not '{application}'."
                ),
            )

        try:
            windows = _get_application_windows("notepad")

            if not windows:
                return self._not_verified(
                    method="notepad_not_open",
                    evidence={
                        "application": "notepad",
                    },
                    message=(
                        "Notepad could not be found while "
                        "verifying typed text."
                    ),
                )

            document_controls = []

            for window in windows:
                try:
                    descendants = window.descendants(control_type="Document")
                    if descendants:
                        document_controls.extend(descendants)
                except Exception:
                    continue

            if not document_controls:
                return self._not_verified(
                    method="notepad_document_not_found",
                    evidence={
                        "application": "notepad",
                    },
                    message=(
                        "The Notepad document control could not "
                        "be located for text verification."
                    ),
                )

            for document in document_controls:
                try:
                    actual_text = document.window_text()
                except Exception:
                    try:
                        actual_text = document.element_info.name
                    except Exception:
                        continue

                if expected_text in actual_text:
                    return {
                        "verified": True,
                        "method": "notepad_editor_text",
                        "evidence": {
                            "application": "notepad",
                            "expected_text": expected_text,
                            "actual_text": actual_text,
                            "match": True,
                        },
                        "message": (
                            "Typed text was independently verified "
                            "inside the Notepad document."
                        ),
                    }

            return self._not_verified(
                method="notepad_text_not_found",
                evidence={
                    "application": "notepad",
                    "expected_text": expected_text,
                },
                message=(
                    "The expected text was not found in the "
                    "observable Notepad document."
                ),
            )

        except Exception as exc:
            return self._not_verified(
                method="notepad_text_verification_error",
                evidence={
                    "application": "notepad",
                    "expected_text": expected_text,
                    "error": str(exc),
                },
                message=(
                    "An error occurred while verifying typed "
                    f"text in Notepad: {exc}"
                ),
            )

    def _verify_browser_type_text(
        self,
        action: Action,
        execution_result: dict[str, Any],
    ) -> dict[str, Any]:
        expected_text = action.arguments.get("text")
        pre_action_state = execution_result.get("pre_action_state") or {}

        if not isinstance(expected_text, str) or not expected_text.strip():
            return self._not_verified(
                method="browser_type_text_missing_text",
                evidence={"expected_text": expected_text},
                message="Cannot verify browser typing because no expected text was provided.",
            )

        page = getattr(browser, "_page", None)

        if page is None:
            return self._not_verified(
                method="browser_text_unverifiable",
                evidence={
                    "browser_open": execution_result.get("browser_open"),
                    "browser_url": execution_result.get("browser_url"),
                    "pre_action_state": pre_action_state,
                },
                message="Browser typing could not be independently verified because no controlled browser page exists.",
            )

        try:
            current_value = None
            current_texts = None

            try:
                current_texts = page.evaluate(
                    """
                    () => {
                        const selectors = [
                            'input:not([type="hidden"]):not([type="submit"]):not([type="button"]):not([type="checkbox"]):not([type="radio"])',
                            'textarea',
                            '[contenteditable="true"]',
                            '[role="textbox"]'
                        ];

                        const matches = [];
                        for (const selector of selectors) {
                            for (const element of document.querySelectorAll(selector)) {
                                const tag = (element.tagName || '').toLowerCase();
                                let value = '';
                                if (tag === 'input' || tag === 'textarea') {
                                    value = element.value || '';
                                } else {
                                    value = element.textContent || element.innerText || '';
                                }
                                matches.push({ tag, value });
                            }
                        }

                        if (matches.length === 0) {
                            const active = document.activeElement;
                            if (active && (active.tagName === 'INPUT' || active.tagName === 'TEXTAREA' || active.isContentEditable)) {
                                const tag = active.tagName.toLowerCase();
                                return [{ tag, value: tag === 'input' || tag === 'textarea' ? active.value || '' : active.textContent || active.innerText || '' }];
                            }
                        }

                        return matches.slice(0, 10);
                    }
                    """
                )
            except Exception:
                current_texts = None

            if isinstance(current_texts, list) and current_texts:
                values: list[str] = []
                for item in current_texts:
                    if isinstance(item, dict):
                        value = item.get("value")
                        if isinstance(value, str):
                            values.append(value)
                    elif isinstance(item, str):
                        values.append(item)

                if values:
                    non_empty = [value for value in values if value]
                    current_value = non_empty[-1] if non_empty else values[-1]

            if current_value is None:
                return self._not_verified(
                    method="browser_text_unverifiable",
                    evidence={
                        "browser_url": execution_result.get("browser_url"),
                        "browser_open": execution_result.get("browser_open"),
                        "pre_action_state": pre_action_state,
                        "page_url": page.url,
                    },
                    message="Browser typing could not be independently verified because the active browser input value was not observable.",
                )

            before_value = None
            if isinstance(pre_action_state, dict):
                before_value = pre_action_state.get("editable_value_before")

            if isinstance(before_value, list):
                before_value = before_value[-1] if before_value else None

            before_value = str(before_value) if before_value is not None else None
            current_value = str(current_value)

            changed = before_value is None or current_value != before_value
            contains_expected = expected_text in current_value

            if contains_expected and changed:
                return {
                    "verified": True,
                    "method": "browser_editable_text",
                    "evidence": {
                        "browser_url": execution_result.get("browser_url") or page.url,
                        "page_url": page.url,
                        "page_title": page.title(),
                        "before_value": before_value,
                        "after_value": current_value,
                        "expected_text": expected_text,
                        "changed": True,
                    },
                    "message": "Browser typing was independently verified by reading the editable DOM value after the action.",
                }

            if contains_expected and not changed:
                return self._not_verified(
                    method="browser_text_mismatch",
                    evidence={
                        "browser_url": execution_result.get("browser_url") or page.url,
                        "page_url": page.url,
                        "page_title": page.title(),
                        "before_value": before_value,
                        "after_value": current_value,
                        "expected_text": expected_text,
                    },
                    message="Browser input value contains the expected text, but the value did not change from its pre-action state.",
                )

            return self._not_verified(
                method="browser_text_missing",
                evidence={
                    "browser_url": execution_result.get("browser_url") or page.url,
                    "page_url": page.url,
                    "page_title": page.title(),
                    "before_value": before_value,
                    "after_value": current_value,
                    "expected_text": expected_text,
                },
                message="The browser input value was readable, but it did not contain the expected text after typing.",
            )

        except Exception as exc:
            return self._not_verified(
                method="browser_text_verification_error",
                evidence={
                    "browser_url": execution_result.get("browser_url"),
                    "page_url": getattr(page, "url", None),
                    "expected_text": expected_text,
                    "error": str(exc),
                },
                message=f"An error occurred while verifying browser text entry: {exc}",
            )

    def _verify_press_key(
        self,
        action: Action,
        execution_result: dict[str, Any],
    ) -> dict[str, Any]:
        key = action.arguments.get("key")

        if not key:
            return self._not_verified(
                method="key_missing",
                message="Cannot verify keyboard action because no key was provided.",
            )

        key = str(key).lower()

        if key not in {"enter", "backspace"}:
            return self._not_verified(
                method="key_outcome_unsupported",
                evidence={
                    "key": key,
                },
                message=(
                    f"Key '{key}' executed successfully, but its "
                    "resulting UI state cannot yet be independently verified."
                ),
            )

        application = execution_result.get("application")

        if not application:
            application = action.arguments.get("application")

        if (
            execution_result.get("browser_open")
            and isinstance(execution_result.get("pre_action_state"), dict)
            and execution_result["pre_action_state"].get("application") == "browser"
        ):
            return self._verify_browser_press_key(
                action,
                execution_result,
            )

        if not application:
            return self._not_verified(
                method="key_missing_application",
                evidence={
                    "key": key,
                },
                message=(
                    f"Cannot verify key '{key}' because the "
                    "target application is unknown."
                ),
            )

        if application != "notepad":
            return self._not_verified(
                method="key_application_unsupported",
                evidence={
                    "application": application,
                    "key": key,
                },
                message=(
                    f"Independent verification for key '{key}' "
                    "is currently implemented only for Notepad."
                ),
            )

        pre_action_state = execution_result.get("pre_action_state")

        if not isinstance(pre_action_state, dict):
            return self._not_verified(
                method="key_pre_state_missing",
                evidence={
                    "application": application,
                    "key": key,
                },
                message=(
                    f"Cannot verify key '{key}' because the "
                    "pre-action document state was not captured."
                ),
            )

        text_before = pre_action_state.get("document_text_before")

        if text_before is None:
            return self._not_verified(
                method="key_pre_state_text_missing",
                evidence={
                    "application": application,
                    "key": key,
                    "pre_action_state": pre_action_state,
                },
                message=(
                    f"Cannot verify key '{key}' because the "
                    "document text before the action was not captured."
                ),
            )

        try:
            windows = _get_application_windows("notepad")

            if not windows:
                return self._not_verified(
                    method="notepad_not_open",
                    evidence={
                        "application": "notepad",
                        "key": key,
                    },
                    message=(
                        f"Notepad could not be found while "
                        f"verifying key '{key}'."
                    ),
                )

            document_controls = []

            for window in windows:
                try:
                    descendants = window.descendants(control_type="Document")
                    if descendants:
                        document_controls.extend(descendants)
                except Exception:
                    continue

            if not document_controls:
                return self._not_verified(
                    method="notepad_document_not_found",
                    evidence={
                        "application": "notepad",
                        "key": key,
                    },
                    message=(
                        f"The Notepad document control could not "
                        f"be located while verifying key '{key}'."
                    ),
                )

            text_after = None

            for document in document_controls:
                try:
                    candidate_text = document.window_text()
                except Exception:
                    try:
                        candidate_text = document.element_info.name
                    except Exception:
                        continue

                if candidate_text is not None:
                    text_after = candidate_text
                    break

            if text_after is None:
                return self._not_verified(
                    method="notepad_document_text_unavailable",
                    evidence={
                        "application": "notepad",
                        "key": key,
                    },
                    message=(
                        f"Notepad document text could not be "
                        f"read while verifying key '{key}'."
                    ),
                )

            if key == "enter":
                document_changed = text_after != text_before
                newline_count_before = text_before.count("\r") + text_before.count("\n")
                newline_count_after = text_after.count("\r") + text_after.count("\n")
                newline_added = newline_count_after > newline_count_before
                ends_with_newline = text_after.endswith("\r") or text_after.endswith("\n")

                # Enter does not necessarily leave the document ending
                # with a newline. If the caret is in the middle of an
                # existing document, Enter inserts a newline between the
                # surrounding text. Therefore, the reliable observable
                # condition is that the document changed and its newline
                # count increased.
                if document_changed and newline_added:
                    return {
                        "verified": True,
                        "method": "notepad_enter_newline",
                        "evidence": {
                            "application": "notepad",
                            "key": "enter",
                            "text_before": text_before,
                            "text_after": text_after,
                            "document_changed": True,
                            "newline_count_before": newline_count_before,
                            "newline_count_after": newline_count_after,
                            "newline_added": True,
                        },
                        "message": (
                            "Enter was independently verified by "
                            "observing an additional newline in Notepad."
                        ),
                    }

                return self._not_verified(
                    method="notepad_enter_outcome_mismatch",
                    evidence={
                        "application": "notepad",
                        "key": "enter",
                        "text_before": text_before,
                        "text_after": text_after,
                        "document_changed": document_changed,
                        "newline_count_before": newline_count_before,
                        "newline_count_after": newline_count_after,
                        "newline_added": newline_added,
                        "ends_with_newline": ends_with_newline,
                    },
                    message=(
                        "Enter executed, but the resulting "
                        "Notepad document state did not provide "
                        "sufficient evidence of a new newline."
                    ),
                )

            if key == "backspace":
                document_changed = text_after != text_before
                expected_length = len(text_before) - 1
                exactly_one_character_removed = (
                    document_changed and len(text_after) == expected_length
                )

                if not exactly_one_character_removed:
                    return self._not_verified(
                        method="notepad_backspace_outcome_mismatch",
                        evidence={
                            "application": "notepad",
                            "key": "backspace",
                            "text_before": text_before,
                            "text_after": text_after,
                            "document_changed": document_changed,
                            "expected_length": expected_length,
                            "actual_length": len(text_after),
                            "exactly_one_character_removed": exactly_one_character_removed,
                        },
                        message=(
                            "Backspace executed, but the resulting "
                            "Notepad document did not show removal "
                            "of exactly one character."
                        ),
                    )

                common_prefix_length = 0

                while (
                    common_prefix_length < len(text_after)
                    and common_prefix_length < len(text_before)
                    and text_after[common_prefix_length] == text_before[common_prefix_length]
                ):
                    common_prefix_length += 1

                removed_index = common_prefix_length
                before_suffix = text_before[removed_index + 1 :]
                after_suffix = text_after[removed_index:]
                surrounding_text_preserved = before_suffix == after_suffix

                if not surrounding_text_preserved:
                    return self._not_verified(
                        method="notepad_backspace_outcome_mismatch",
                        evidence={
                            "application": "notepad",
                            "key": "backspace",
                            "text_before": text_before,
                            "text_after": text_after,
                            "document_changed": document_changed,
                            "character_count_decreased": (
                                len(text_after) == len(text_before) - 1
                            ),
                            "surrounding_text_preserved": False,
                        },
                        message=(
                            "Backspace executed and the document "
                            "length decreased, but the resulting "
                            "text did not match the expected "
                            "single-character removal pattern."
                        ),
                    )

                removed_character = text_before[removed_index]

                return {
                    "verified": True,
                    "method": "notepad_backspace_character_removed",
                    "evidence": {
                        "application": "notepad",
                        "key": "backspace",
                        "text_before": text_before,
                        "text_after": text_after,
                        "document_changed": True,
                        "character_removed": True,
                        "removed_character": removed_character,
                        "removed_index": removed_index,
                        "surrounding_text_preserved": True,
                    },
                    "message": (
                        "Backspace was independently verified "
                        "by observing the removal of exactly "
                        "one character from Notepad."
                    ),
                }

            return self._not_verified(
                method="key_outcome_unsupported",
                evidence={
                    "application": application,
                    "key": key,
                },
                message=(
                    f"Key '{key}' executed successfully, but its "
                    "resulting UI state cannot yet be independently verified."
                ),
            )

        except Exception as exc:
            return self._not_verified(
                method="key_verification_error",
                evidence={
                    "application": application,
                    "key": key,
                    "error": str(exc),
                },
                message=(
                    f"An error occurred while verifying key "
                    f"'{key}' in Notepad: {exc}"
                ),
            )

    def _verify_browser_press_key(
        self,
        action: Action,
        execution_result: dict[str, Any],
    ) -> dict[str, Any]:
        key = str(action.arguments.get("key", "")).lower()
        before = execution_result.get("pre_action_state")
        after = execution_result.get("post_action_state")

        if not isinstance(before, dict) or not isinstance(after, dict):
            return self._not_verified(
                method="browser_key_state_missing",
                evidence={
                    "key": key,
                    "pre_action_state": before,
                    "post_action_state": after,
                },
                message=(
                    f"Cannot verify browser key '{key}' because "
                    "the browser state transition was not captured."
                ),
            )

        before_url = before.get("browser_url")
        after_url = after.get("browser_url")
        before_title = before.get("browser_title")
        after_title = after.get("browser_title")
        before_values = before.get("editable_values", [])
        after_values = after.get("editable_values", [])

        url_changed = before_url != after_url
        title_changed = (
            isinstance(before_title, str)
            and isinstance(after_title, str)
            and bool(after_title)
            and before_title != after_title
        )
        editable_state_changed = before_values != after_values

        if not (
            url_changed
            or title_changed
            or editable_state_changed
        ):
            return self._not_verified(
                method="browser_key_state_unchanged",
                evidence={
                    "key": key,
                    "before_url": before_url,
                    "after_url": after_url,
                    "before_title": before_title,
                    "after_title": after_title,
                    "before_editable_values": before_values,
                    "after_editable_values": after_values,
                },
                message=(
                    f"Browser key '{key}' executed, but no meaningful "
                    "observable browser state transition was detected."
                ),
            )

        return {
            "verified": True,
            "method": "browser_key_state_transition",
            "evidence": {
                "key": key,
                "before_url": before_url,
                "after_url": after_url,
                "before_title": before_title,
                "after_title": after_title,
                "before_editable_values": before_values,
                "after_editable_values": after_values,
                "url_changed": url_changed,
                "title_changed": title_changed,
                "editable_state_changed": editable_state_changed,
            },
            "message": (
                f"Browser key '{key}' was independently verified "
                "by an observable browser state transition."
            ),
        }

    def _verify_hotkey(
        self,
        action: Action,
        execution_result: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Verify a desktop hotkey action.

        A generic hotkey can have application-specific semantic effects
        that are not reliably observable through the current desktop
        verification layer. Therefore, for supported foreground
        applications, this method verifies the part AXE can prove:
        successful dispatch of the requested hotkey.

        This intentionally does not claim that the application's internal
        semantic effect was independently observed.
        """
        keys = action.arguments.get("keys")

        if not isinstance(keys, list) or not keys:
            return self._not_verified(
                method="hotkey_missing_keys",
                evidence={
                    "keys": keys,
                    "execution_result": execution_result,
                },
                message=(
                    "Cannot verify hotkey execution because no "
                    "hotkey keys were provided."
                ),
            )

        normalized_keys = [str(key).lower().strip() for key in keys]

        if not execution_result.get("success"):
            return self._not_verified(
                method="hotkey_execution_failed",
                evidence={
                    "keys": normalized_keys,
                    "execution_result": execution_result,
                },
                message="Hotkey action did not execute successfully.",
            )

        application = execution_result.get("application")

        if not application:
            application = action.arguments.get("application")

        # Browser hotkeys already have a dedicated state-transition
        # verifier for press_key. Generic browser hotkeys remain
        # dispatch-verifiable only because their semantic effect depends
        # on the specific browser/page context.
        if application == "browser" or execution_result.get("browser_open"):
            return {
                "verified": True,
                "method": "hotkey_dispatched_to_browser",
                "evidence": {
                    "application": "browser",
                    "keys": normalized_keys,
                    "execution_success": True,
                    "semantic_ui_effect_verified": False,
                },
                "message": (
                    f"Hotkey '{'+'.join(normalized_keys)}' was successfully "
                    "dispatched to the controlled browser. The hotkey "
                    "dispatch is verified, but its application-specific "
                    "semantic effect is not independently observable."
                ),
            }

        if not application:
            return self._not_verified(
                method="hotkey_missing_application",
                evidence={
                    "keys": normalized_keys,
                    "execution_result": execution_result,
                },
                message=(
                    f"Hotkey '{'+'.join(normalized_keys)}' executed "
                    "successfully, but the target application could not "
                    "be identified for dispatch verification."
                ),
            )

        return {
            "verified": True,
            "method": "hotkey_dispatched_to_foreground_application",
            "evidence": {
                "application": application,
                "keys": normalized_keys,
                "execution_success": True,
                "semantic_ui_effect_verified": False,
            },
            "message": (
                f"Hotkey '{'+'.join(normalized_keys)}' was successfully "
                f"dispatched to the foreground application '{application}'. "
                "The hotkey dispatch is verified, but the application's "
                "internal semantic effect is not independently observable."
            ),
        }

    def _not_verified(
        self,
        method: str,
        message: str,
        evidence: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "verified": False,
            "method": method,
            "evidence": evidence or {},
            "message": message,
        }