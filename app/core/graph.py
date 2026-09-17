"""LangGraph orchestration layer for AXE."""

from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.core.planner import AXEPlanner
from app.core.runtime import AXERuntime
from app.core.validator import AXEValidator


class AXEGraphState(TypedDict, total=False):
    """State carried through the AXE LangGraph workflow."""

    message: str
    user_approved: bool | None
    task: Any
    validation: dict[str, Any]
    safety: dict[str, Any]
    approval: dict[str, Any]
    execution_result: dict[str, Any]
    error: str | None


class AXEGraph:
    """LangGraph orchestration for the AXE execution pipeline."""

    def __init__(
        self,
        planner: AXEPlanner | None = None,
        validator: AXEValidator | None = None,
        runtime: AXERuntime | None = None,
    ) -> None:
        self.planner = planner or AXEPlanner()
        self.validator = validator or AXEValidator()
        self.runtime = runtime or AXERuntime()

        self.graph = self._build_graph()

    def _build_graph(self):
        """Build and compile the AXE LangGraph workflow."""

        workflow = StateGraph(AXEGraphState)

        workflow.add_node(
            "plan",
            self._plan_node,
        )

        workflow.add_node(
            "validate",
            self._validate_node,
        )

        workflow.add_node(
            "safety",
            self._safety_node,
        )

        workflow.add_node(
            "execute",
            self._execute_node,
        )

        workflow.add_edge(
            START,
            "plan",
        )

        workflow.add_edge(
            "plan",
            "validate",
        )

        workflow.add_conditional_edges(
            "validate",
            self._validation_router,
            {
                "safety": "safety",
                "error": END,
            },
        )

        workflow.add_conditional_edges(
            "safety",
            self._safety_router,
            {
                "execute": "execute",
                "approval_required": END,
                "blocked": END,
                "error": END,
            },
        )

        workflow.add_edge(
            "execute",
            END,
        )

        return workflow.compile()

    def _plan_node(
        self,
        state: AXEGraphState,
    ) -> AXEGraphState:
        """Create a structured task from the user message."""

        message = state.get("message")

        if not isinstance(message, str):
            return {
                "error": (
                    "Invalid graph state: "
                    "message must be a string."
                ),
            }

        message = message.strip()

        if not message:
            return {
                "error": "No user message was provided.",
            }

        try:
            task = self.planner.plan(message)

            return {
                "task": task,
                "error": None,
            }

        except Exception as exc:
            return {
                "error": (
                    "Planning failed: "
                    f"{exc}"
                ),
            }

    def _validate_node(
        self,
        state: AXEGraphState,
    ) -> AXEGraphState:
        """Validate the planned task before safety evaluation."""

        if state.get("error"):
            return state

        task = state.get("task")

        if task is None:
            return {
                **state,
                "error": (
                    "No task was produced "
                    "by the planner."
                ),
            }

        try:
            validation = self.validator.validate_task(
                task
            )

            if not validation.get(
                "valid",
                False,
            ):
                errors = validation.get(
                    "errors",
                    [],
                )

                error_message = (
                    "Task validation failed."
                )

                if errors:
                    error_message += (
                        f" {' '.join(errors)}"
                    )

                return {
                    **state,
                    "validation": validation,
                    "error": error_message,
                }

            return {
                **state,
                "validation": validation,
                "error": None,
            }

        except Exception as exc:
            return {
                **state,
                "error": (
                    "Validation failed: "
                    f"{exc}"
                ),
            }

    def _validation_router(
        self,
        state: AXEGraphState,
    ) -> str:
        """Route valid tasks to safety evaluation."""

        if state.get("error"):
            return "error"

        validation = state.get(
            "validation",
            {},
        )

        if validation.get(
            "valid",
            False,
        ):
            return "safety"

        return "error"

    def _safety_node(
        self,
        state: AXEGraphState,
    ) -> AXEGraphState:
        """
        Evaluate task safety and approval requirements.

        The same Safety Engine and Approval Gate used by
        AXE Runtime are used here. Runtime remains the
        final enforcement boundary before execution.
        """

        if state.get("error"):
            return state

        task = state.get("task")

        if task is None:
            return {
                **state,
                "error": (
                    "No task is available "
                    "for safety evaluation."
                ),
            }

        try:
            safety_result = (
                self.runtime.safety_engine.classify_task(
                    task.actions
                )
            )

            if not safety_result.get(
                "allowed",
                False,
            ):
                return {
                    **state,
                    "safety": safety_result,
                    "approval": {
                        "approved": False,
                        "requires_approval": False,
                        "decision": "blocked",
                        "reason": safety_result.get(
                            "reason",
                            "Task was blocked by the AXE safety policy.",
                        ),
                    },
                    "error": safety_result.get(
                        "reason",
                        "Task was blocked by the AXE safety policy.",
                    ),
                }

            user_approved = state.get(
                "user_approved",
                None,
            )

            approval_result = (
                self.runtime.approval_gate.evaluate(
                    safety_result,
                    user_approved,
                )
            )

            if not approval_result.get(
                "approved",
                False,
            ):
                return {
                    **state,
                    "safety": safety_result,
                    "approval": approval_result,
                    "error": None,
                }

            return {
                **state,
                "safety": safety_result,
                "approval": approval_result,
                "error": None,
            }

        except Exception as exc:
            return {
                **state,
                "error": (
                    "Safety evaluation failed: "
                    f"{exc}"
                ),
            }

    def _safety_router(
        self,
        state: AXEGraphState,
    ) -> str:
        """Route the task based on safety and approval state."""

        if state.get("error"):
            safety = state.get(
                "safety",
                {},
            )

            if not safety.get(
                "allowed",
                False,
            ):
                return "blocked"

            return "error"

        approval = state.get(
            "approval",
            {},
        )

        if approval.get(
            "approved",
            False,
        ):
            return "execute"

        if approval.get(
            "decision"
        ) == "approval_required":
            return "approval_required"

        if approval.get(
            "decision"
        ) == "human_rejected":
            return "blocked"

        return "blocked"

    def _execute_node(
        self,
        state: AXEGraphState,
    ) -> AXEGraphState:
        """Execute the approved task through AXE Runtime."""

        if state.get("error"):
            return state

        task = state.get("task")

        if task is None:
            return {
                **state,
                "error": (
                    "No task is available "
                    "for execution."
                ),
            }

        try:
            result = self.runtime.execute_task(
                task,
                user_approved=state.get(
                    "user_approved",
                    None,
                ),
            )

            if not isinstance(
                result,
                dict,
            ):
                return {
                    **state,
                    "error": (
                        "Runtime returned "
                        "an invalid result."
                    ),
                }

            return {
                **state,
                "execution_result": result,
                "error": (
                    None
                    if result.get(
                        "success",
                        False,
                    )
                    else result.get(
                        "message",
                        "Task execution failed.",
                    )
                ),
            }

        except Exception as exc:
            return {
                **state,
                "error": (
                    "Execution failed: "
                    f"{exc}"
                ),
            }

    def invoke(
        self,
        message: str,
        user_approved: bool | None = None,
    ) -> AXEGraphState:
        """Run an AXE request through LangGraph."""

        if not isinstance(
            message,
            str,
        ):
            return {
                "message": "",
                "error": (
                    "Graph input message "
                    "must be a string."
                ),
            }

        initial_state: AXEGraphState = {
            "message": message,
            "user_approved": user_approved,
            "error": None,
        }

        return self.graph.invoke(
            initial_state
        )