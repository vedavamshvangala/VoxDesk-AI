"""AXE execution runtime and execution-context management."""

from typing import Any

from app.core.approval import AXEApprovalGate
from app.core.executor import TaskExecutor
from app.core.safety import AXESafetyEngine
from app.core.task import Action, Task
from app.core.tool_registry import get_tool_registry
from app.core.verifier import AXEVerifier
from app.tools import browser as browser_module
from app.tools.desktop import (
    _get_application_windows,
    _get_explorer_shell_windows,
    get_active_window,
)
from app.tools.applications import get_application


class AXERuntime:
    """
    Runtime environment responsible for initializing AXE's
    approved tools, maintaining execution context, enforcing
    safety and approval policies, executing structured tasks,
    and verifying observable results.

    Execution flow:

        Safety
            ↓
        Approval
            ↓
        Executor
            ↓
        Verification

    The runtime maintains the currently active application and
    browser context so that actions can be verified against
    state established earlier in the same task.
    """

    def __init__(self) -> None:
        self.executor = TaskExecutor()
        self.verifier = AXEVerifier()

        # Safety and human-approval controls.
        self.safety_engine = AXESafetyEngine()
        self.approval_gate = AXEApprovalGate()

        # Execution context for the currently running task.
        self.active_application: str | None = None
        self.browser_open: bool = False
        self.browser_url: str | None = None

        # Bounded automatic recovery.
        self.max_retries: int = 1

        self._register_tools()

    def _register_tools(self) -> None:
        """
        Register all approved AXE tools with the executor.
        """

        tools = get_tool_registry()

        for name, function in tools.items():
            self.executor.register_tool(
                name,
                function,
            )

    def _detect_active_application(self) -> str | None:
        """
        Detect the currently focused supported desktop application.

        This is used for standalone keyboard actions such as
        "press Enter", where the planner intentionally does not add
        an application argument. The foreground window is mapped
        against the same application definitions used by AXE's
        desktop tools.
        """
        try:
            active = get_active_window()

            if not isinstance(active, dict) or not active.get("success"):
                return None

            active_hwnd = active.get("hwnd")
            active_process_name = active.get("process_name")

            if not active_process_name:
                return None

            active_process_name = str(active_process_name).lower()

            # File Explorer uses shell windows rather than a normal
            # application process mapping.
            if active_hwnd:
                try:
                    for shell_window in _get_explorer_shell_windows():
                        if shell_window.get("hwnd") == active_hwnd:
                            return "file_explorer"
                except Exception:
                    pass

            # Match the foreground process against each supported
            # application's configured process/window process names.
            try:
                from app.tools.applications import get_allowed_applications

                allowed_applications = get_allowed_applications()
            except Exception:
                allowed_applications = ()

            for application in allowed_applications:
                try:
                    definition = get_application(application)

                    if definition is None:
                        continue

                    process_names = []

                    if getattr(definition, "window_process_names", None):
                        process_names.extend(
                            str(name).lower()
                            for name in definition.window_process_names
                        )

                    process_name = getattr(definition, "process_name", None)
                    if process_name:
                        process_names.append(str(process_name).lower())

                    if active_process_name in set(process_names):
                        return definition.name

                except Exception:
                    continue

        except Exception:
            return None

        return None

    def _capture_browser_editable_state(self) -> dict[str, Any]:
        """Capture the current browser editable-field state if a controlled page exists."""

        page = getattr(browser_module, "_page", None)

        if page is None:
            return {}

        try:
            payload = page.evaluate(
                """
                () => {
                    const selectors = [
                        'input:not([type="hidden"]):not([type="submit"]):not([type="button"]):not([type="checkbox"]):not([type="radio"])',
                        'textarea',
                        '[contenteditable="true"]',
                        '[role="textbox"]',
                    ];

                    const values = [];
                    const seen = new Set();

                    for (const selector of selectors) {
                        for (const element of document.querySelectorAll(selector)) {
                            const tag = (element.tagName || '').toLowerCase();
                            let value = '';

                            if (tag === 'input' || tag === 'textarea') {
                                value = element.value || '';
                            } else {
                                value = element.textContent || element.innerText || '';
                            }

                            const label = (
                                element.getAttribute('aria-label')
                                || element.getAttribute('name')
                                || element.getAttribute('placeholder')
                                || ''
                            ).trim();

                            const key = `${tag}|${value}|${label}`;

                            if (!seen.has(key)) {
                                seen.add(key);
                                values.push({
                                    tag,
                                    value,
                                    label,
                                });
                            }
                        }
                    }

                    if (values.length === 0) {
                        const active = document.activeElement;

                        if (active && active instanceof HTMLElement) {
                            const tag = active.tagName.toLowerCase();
                            let value = '';

                            if (tag === 'input' || tag === 'textarea') {
                                value = active.value || '';
                            } else {
                                value = active.textContent || active.innerText || '';
                            }

                            if (value || tag === 'input' || tag === 'textarea') {
                                return [{ tag, value, label: active.getAttribute('aria-label') || active.getAttribute('name') || active.getAttribute('placeholder') || '' }];
                            }
                        }
                    }

                    return values.slice(0, 10);
                }
                """
            )

            if not isinstance(payload, list):
                return {}

            values = [
                str(item.get("value", ""))
                for item in payload
                if isinstance(item, dict)
            ]

            if not values:
                return {}

            return {
                "browser_url": page.url,
                "browser_title": page.title(),
                "editable_values": values,
                "editable_value_before": values[0],
            }
        except Exception:
            return {}

    def _capture_pre_action_state(
        self,
        action: Action,
    ) -> dict[str, Any]:
        """
        Capture observable state immediately before executing
        an action when that state is useful for verification.

        This captures the Notepad document text for keyboard
        actions and the current editable browser value for text
        entry in the active browser context.
        """

        if not isinstance(action, Action):
            return {}

        tool = action.tool.strip()

        # Standalone hotkeys such as "press Ctrl+A" intentionally do not
        # require the planner to add an application argument. Resolve the
        # actual Windows foreground application before execution so the
        # verifier can prove that the hotkey was dispatched to the
        # intended foreground application.
        if tool == "hotkey":
            if self.active_application is None:
                detected_application = self._detect_active_application()

                if detected_application:
                    self.active_application = detected_application

            if self.active_application:
                return {
                    "application": self.active_application,
                }

            return {}

        if tool == "press_key":
            # A standalone keyboard command such as "press Enter"
            # intentionally has no application argument. If the task
            # has not already established an active application,
            # resolve the actual Windows foreground application now.
            if self.active_application is None:
                detected_application = self._detect_active_application()

                if detected_application:
                    self.active_application = detected_application

            if self.active_application != "notepad":
                if self.browser_open or getattr(browser_module, "_page", None) is not None:
                    state = self._capture_browser_editable_state()

                    if state:
                        return {
                            "application": "browser",
                            **state,
                        }

                return {}

            key = action.arguments.get("key")

            if not isinstance(key, str):
                return {}

            if key.strip().lower() not in {
                "enter",
                "backspace",
                "delete",
                "tab",
            }:
                return {}

            windows = _get_application_windows("notepad")

            if not windows:
                return {}

            document_controls = [
                control
                for control in windows[0].descendants()
                if control.element_info.control_type == "Document"
            ]

            if not document_controls:
                return {}

            texts: list[str] = []

            for document in document_controls:
                try:
                    text = document.window_text()

                    if isinstance(text, str):
                        texts.append(text)
                except Exception:
                    continue

            if not texts:
                return {}

            return {
                "application": "notepad",
                "document_text_before": texts[0],
            }

        if tool == "type_text":
            # Determine the real foreground application before typing.
            # This is important for standalone commands because the planner
            # may intentionally omit an application argument.
            if self.active_application is None:
                detected_application = self._detect_active_application()

                if detected_application:
                    self.active_application = detected_application

            # Browser typing is handled through the controlled browser
            # session when a browser page is actually active.
            if (
                self.browser_open
                or getattr(browser_module, "_page", None) is not None
            ):
                state = self._capture_browser_editable_state()

                if state:
                    return {
                        "application": "browser",
                        **state,
                    }

            # Capture Notepad's observable document state before typing.
            # This gives the verifier an independent before/after state
            # transition instead of relying only on the executor result.
            if self.active_application == "notepad":
                try:
                    windows = _get_application_windows("notepad")

                    if not windows:
                        return {
                            "application": "notepad",
                        }

                    document_controls = []

                    for window in windows:
                        try:
                            descendants = window.descendants(
                                control_type="Document"
                            )

                            if descendants:
                                document_controls.extend(descendants)
                        except Exception:
                            continue

                    if not document_controls:
                        return {
                            "application": "notepad",
                        }

                    for document in document_controls:
                        try:
                            document_text = document.window_text()

                            if isinstance(document_text, str):
                                return {
                                    "application": "notepad",
                                    "document_text_before": document_text,
                                }
                        except Exception:
                            continue

                    return {
                        "application": "notepad",
                    }

                except Exception:
                    return {
                        "application": "notepad",
                    }

            return {}

    def _update_execution_context(
        self,
        action: Action,
        execution_result: dict[str, Any],
    ) -> None:
        """
        Update the runtime's execution context from the action
        that was executed.

        Application context and browser context are intentionally
        maintained by the runtime instead of being added to every
        Action object.
        """

        if not isinstance(action, Action):
            return

        if not isinstance(execution_result, dict):
            return

        tool = action.tool.strip()

        # ---------------------------------------------------------
        # Desktop application context
        # ---------------------------------------------------------
        if tool in {
            "open_application",
            "focus_application",
            "verify_application",
        }:
            application = action.arguments.get("application")

            if isinstance(application, str) and application.strip():
                if execution_result.get("success", False):
                    self.active_application = (
                        application.strip().lower()
                    )

        # ---------------------------------------------------------
        # Browser context
        # ---------------------------------------------------------
        if tool == "open_browser":
            if execution_result.get("success", False):
                self.browser_open = True

                url = execution_result.get("url")

                if isinstance(url, str):
                    self.browser_url = url

        elif tool in {
            "navigate_browser",
            "verify_browser",
        }:
            if execution_result.get("success", False):
                self.browser_open = True

                url = execution_result.get("url")

                if isinstance(url, str) and url.strip():
                    self.browser_url = url.strip()

        elif tool == "close_browser":
            if execution_result.get("success", False):
                self.browser_open = False
                self.browser_url = None

    def _build_verification_result(
        self,
        action: Action,
        execution_result: dict[str, Any],
        pre_action_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Build verification input while preserving the original
        execution result and relevant execution context.
        """

        verification_input = dict(execution_result)

        if self.active_application:
            verification_input["application"] = (
                self.active_application
            )

        if self.browser_open:
            verification_input["browser_open"] = True

        if self.browser_url:
            verification_input["browser_url"] = (
                self.browser_url
            )

        if pre_action_state:
            verification_input["pre_action_state"] = (
                pre_action_state
            )

        return self.verifier.verify_action(
            action,
            verification_input,
        )

    def _check_action_safety(
        self,
        action: Action,
        user_approved: bool | None = None,
    ) -> dict[str, Any]:
        """
        Evaluate an action through the AXE Safety Engine and
        Approval Gate before execution.

        No action reaches the executor unless the resulting
        approval decision allows execution.
        """

        safety_result = self.safety_engine.classify_action(
            action
        )

        approval_result = self.approval_gate.evaluate(
            safety_result,
            user_approved,
        )

        return {
            "safety": safety_result,
            "approval": approval_result,
            "allowed": approval_result.get(
                "approved",
                False,
            ),
        }

    def execute_action(
        self,
        action: Action,
        user_approved: bool | None = None,
    ) -> dict[str, Any]:
        """
        Execute a single structured AXE action.

        Safety and approval are evaluated before execution.

        If the action is unsafe, unknown, critical, or requires
        approval that has not been granted, execution does not
        reach the TaskExecutor.
        """

        safety_check = self._check_action_safety(
            action,
            user_approved,
        )

        if not safety_check["allowed"]:
            approval_result = safety_check["approval"]

            return {
                "success": False,
                "verified": False,
                "tool": (
                    action.tool
                    if isinstance(action, Action)
                    else None
                ),
                "result": None,
                "message": approval_result.get(
                    "reason",
                    "Action was blocked by the AXE safety policy.",
                ),
                "safety": safety_check["safety"],
                "approval": approval_result,
            }

        pre_action_state = self._capture_pre_action_state(
            action
        )

        if action.tool == "type_text" and (
            self.browser_open
            or getattr(browser_module, "_page", None) is not None
        ):
            focus_result = browser_module.focus_editable()

            if not focus_result.get("success") or not focus_result.get("focused"):
                execution_result = {
                    "success": False,
                    "tool": action.tool,
                    "result": focus_result,
                    "message": focus_result.get(
                        "message",
                        "Browser editable focus could not be confirmed.",
                    ),
                    "browser_open": True,
                }

                verification_result = self._build_verification_result(
                    action,
                    execution_result,
                    pre_action_state,
                )

                return {
                    **execution_result,
                    "safety": safety_check["safety"],
                    "approval": safety_check["approval"],
                    "verification": verification_result,
                    "verified": verification_result.get(
                        "verified",
                        False,
                    ),
                }

        execution_result = self.executor.execute_action(
            action
        )

        if action.tool == "press_key" and (
            self.browser_open
            or getattr(browser_module, "_page", None) is not None
        ):
            page = getattr(browser_module, "_page", None)

            if page is not None:
                try:
                    page.wait_for_timeout(250)
                except Exception:
                    pass

            post_action_state = self._capture_browser_editable_state()

            if post_action_state:
                execution_result["post_action_state"] = post_action_state

        self._update_execution_context(
            action,
            execution_result,
        )

        verification_result = self._build_verification_result(
            action,
            execution_result,
            pre_action_state,
        )

        return {
            **execution_result,
            "safety": safety_check["safety"],
            "approval": safety_check["approval"],
            "verification": verification_result,
            "verified": verification_result.get(
                "verified",
                False,
            ),
        }

    def execute_task(
        self,
        task: Task,
        user_approved: bool | None = None,
    ) -> dict[str, Any]:
        """
        Execute all actions contained in a structured AXE task.

        The complete task is first evaluated by the Safety Engine.

        Each action is then independently passed through the
        safety and approval gate before execution.

        Each successfully executed action is independently
        verified before the next action is executed.

        The active application and browser context are reset at
        the start of every new task so that context cannot leak
        between unrelated user requests.
        """

        if not isinstance(task, Task):
            return {
                "success": False,
                "verified": False,
                "message": "Invalid AXE task.",
                "results": [],
            }

        if not task.actions:
            return {
                "success": False,
                "verified": False,
                "completed_steps": 0,
                "total_steps": 0,
                "results": [],
                "message": "AXE task contains no executable actions.",
            }

        # Evaluate the complete task before executing anything.
        task_safety = self.safety_engine.classify_task(
            task.actions
        )

        if not task_safety.get("allowed", False):
            return {
                "success": False,
                "verified": False,
                "completed_steps": 0,
                "total_steps": len(task.actions),
                "results": [],
                "safety": task_safety,
                "message": task_safety.get(
                    "reason",
                    "AXE task was blocked by the safety policy.",
                ),
            }

        # If the task contains medium/high-risk actions and no
        # explicit approval has been supplied, stop before
        # executing any action.
        if (
            task_safety.get("requires_approval", False)
            and user_approved is not True
        ):
            approval_result = self.approval_gate.evaluate(
                task_safety,
                user_approved,
            )

            return {
                "success": False,
                "verified": False,
                "completed_steps": 0,
                "total_steps": len(task.actions),
                "results": [],
                "safety": task_safety,
                "approval": approval_result,
                "message": approval_result.get(
                    "reason",
                    "Human approval is required before execution.",
                ),
            }

        # Start every task with a clean execution context.
        self.active_application = None
        self.browser_open = False
        self.browser_url = None

        results = []

        for index, action in enumerate(
            task.actions,
            start=1,
        ):
            attempts = 0
            result = self.execute_action(
                action,
                user_approved=user_approved,
            )

            # Retry only an actual execution failure. A successful action
            # followed by failed verification is never blindly re-executed,
            # because repeating a side effect could duplicate the action.
            while (
                not result.get("success", False)
                and attempts < self.max_retries
            ):
                safety = result.get("safety", {})
                approval = result.get("approval", {})

                # Safety/approval failures are terminal and must never be
                # retried automatically.
                if (
                    not safety.get("allowed", True)
                    or approval.get("decision")
                    in {"approval_required", "human_rejected", "blocked"}
                ):
                    break

                attempts += 1
                result = self.execute_action(
                    action,
                    user_approved=user_approved,
                )

            results.append(
                {
                    "step": index,
                    "attempts": attempts + 1,
                    "recovered": attempts > 0 and result.get("success", False),
                    **result,
                }
            )

            if not result.get("success", False):
                return {
                    "success": False,
                    "verified": False,
                    "completed_steps": index - 1,
                    "total_steps": len(task.actions),
                    "results": results,
                    "safety": task_safety,
                    "message": (
                        f"Task stopped at step {index} "
                        f"because tool '{action.tool}' "
                        "could not be executed after "
                        f"{attempts + 1} attempt(s)."
                    ),
                }

            if not result.get("verified", False):
                return {
                    "success": False,
                    "verified": False,
                    "completed_steps": index - 1,
                    "total_steps": len(task.actions),
                    "results": results,
                    "safety": task_safety,
                    "message": (
                        f"Task stopped at step {index} "
                        f"because tool '{action.tool}' "
                        "executed but its result could not "
                        "be independently verified."
                    ),
                }

        return {
            "success": True,
            "verified": True,
            "completed_steps": len(task.actions),
            "total_steps": len(task.actions),
            "results": results,
            "safety": task_safety,
            "message": (
                "Task executed and independently verified "
                "successfully."
            ),
        }

    def available_tools(self) -> list[str]:
        """
        Return the names of tools currently available to AXE.
        """

        return list(self.executor.tools.keys())