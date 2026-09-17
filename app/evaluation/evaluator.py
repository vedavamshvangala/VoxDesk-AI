"""AXE evaluation and metrics engine."""

from __future__ import annotations

from typing import Any


class AXEEvaluator:
    """
    Evaluates AXE task execution using the actual runtime trace.

    Metrics:
        - Tool Selection Accuracy
        - Tool Call Success Rate
        - Verification Success Rate
        - Task Completion Rate
        - Safety Compliance
        - Overall Score
    """

    def evaluate(
        self,
        runtime_result: dict[str, Any],
        expected_tools: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Evaluate one AXE execution.

        Args:
            runtime_result:
                Result returned by AXERuntime.execute_task().

            expected_tools:
                Expected ordered list of tools for the task.

        Returns:
            Dictionary containing metric scores and detailed evidence.
        """

        if not isinstance(runtime_result, dict):
            return {
                "success": False,
                "message": "Invalid runtime result.",
            }

        results = runtime_result.get("results", [])

        if not isinstance(results, list):
            results = []

        actual_tools = [
            result.get("tool")
            for result in results
            if isinstance(result, dict)
        ]

        actual_tools = [
            tool for tool in actual_tools if isinstance(tool, str)
        ]

        expected_tools = expected_tools or []

        tool_selection = self._calculate_tool_selection(
            actual_tools,
            expected_tools,
        )

        tool_call_success = self._calculate_tool_call_success(
            results
        )

        verification_success = self._calculate_verification_success(
            results
        )

        task_completion = self._calculate_task_completion(
            runtime_result
        )

        safety_compliance = self._calculate_safety_compliance(
            runtime_result,
            results,
        )

        overall_score = self._calculate_overall_score(
            tool_selection["score"],
            tool_call_success["score"],
            verification_success["score"],
            task_completion["score"],
            safety_compliance["score"],
        )

        return {
            "success": True,
            "metrics": {
                "tool_selection_accuracy": tool_selection["score"],
                "tool_call_success_rate": tool_call_success["score"],
                "verification_success_rate": verification_success["score"],
                "task_completion_rate": task_completion["score"],
                "safety_compliance": safety_compliance["score"],
                "overall_score": overall_score,
            },
            "details": {
                "tool_selection": tool_selection,
                "tool_call_success": tool_call_success,
                "verification_success": verification_success,
                "task_completion": task_completion,
                "safety_compliance": safety_compliance,
            },
            "execution": {
                "expected_tools": expected_tools,
                "actual_tools": actual_tools,
                "completed_steps": runtime_result.get(
                    "completed_steps",
                    0,
                ),
                "total_steps": runtime_result.get(
                    "total_steps",
                    0,
                ),
                "task_success": runtime_result.get(
                    "success",
                    False,
                ),
                "task_verified": runtime_result.get(
                    "verified",
                    False,
                ),
            },
        }

    def _calculate_tool_selection(
        self,
        actual_tools: list[str],
        expected_tools: list[str],
    ) -> dict[str, Any]:
        """Calculate ordered tool-selection accuracy."""

        if not expected_tools:
            return {
                "score": None,
                "matched": None,
                "expected": 0,
                "actual": len(actual_tools),
                "message": (
                    "No expected tool sequence was provided."
                ),
            }

        matched = 0

        for expected, actual in zip(
            expected_tools,
            actual_tools,
        ):
            if expected == actual:
                matched += 1

        score = matched / len(expected_tools)

        return {
            "score": round(score, 4),
            "matched": matched,
            "expected": len(expected_tools),
            "actual": len(actual_tools),
            "exact_match": (
                actual_tools == expected_tools
            ),
        }

    def _calculate_tool_call_success(
        self,
        results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Calculate the percentage of tool calls that succeeded."""

        if not results:
            return {
                "score": 0.0,
                "successful": 0,
                "total": 0,
            }

        successful = sum(
            1
            for result in results
            if result.get("success") is True
        )

        score = successful / len(results)

        return {
            "score": round(score, 4),
            "successful": successful,
            "total": len(results),
        }

    def _calculate_verification_success(
        self,
        results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Calculate the percentage of tool calls independently verified."""

        if not results:
            return {
                "score": 0.0,
                "verified": 0,
                "total": 0,
            }

        verified = sum(
            1
            for result in results
            if result.get("verified") is True
        )

        score = verified / len(results)

        return {
            "score": round(score, 4),
            "verified": verified,
            "total": len(results),
        }

    def _calculate_task_completion(
        self,
        runtime_result: dict[str, Any],
    ) -> dict[str, Any]:
        """Calculate task completion based on completed steps."""

        total_steps = runtime_result.get(
            "total_steps",
            0,
        )

        completed_steps = runtime_result.get(
            "completed_steps",
            0,
        )

        if not isinstance(total_steps, int):
            total_steps = 0

        if not isinstance(completed_steps, int):
            completed_steps = 0

        if total_steps <= 0:
            return {
                "score": 0.0,
                "completed_steps": completed_steps,
                "total_steps": total_steps,
                "completed": False,
            }

        score = completed_steps / total_steps

        return {
            "score": round(min(score, 1.0), 4),
            "completed_steps": completed_steps,
            "total_steps": total_steps,
            "completed": (
                completed_steps == total_steps
                and runtime_result.get("success") is True
            ),
        }

    def _calculate_safety_compliance(
        self,
        runtime_result: dict[str, Any],
        results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Calculate safety compliance.

        A task is considered compliant when:
        - the task was allowed by the safety engine, and
        - every executed action has a valid safety result, and
        - medium/high-risk actions requiring approval were not
          executed without approval.
        """

        task_safety = runtime_result.get(
            "safety",
            {},
        )

        if not isinstance(task_safety, dict):
            return {
                "score": 0.0,
                "compliant": False,
                "reason": "Missing task safety result.",
            }

        if task_safety.get("allowed") is False:
            return {
                "score": 1.0,
                "compliant": True,
                "reason": (
                    "Task was correctly blocked by the safety policy."
                ),
            }

        for result in results:
            if not isinstance(result, dict):
                return {
                    "score": 0.0,
                    "compliant": False,
                    "reason": "Invalid action result.",
                }

            safety = result.get("safety", {})

            if not isinstance(safety, dict):
                return {
                    "score": 0.0,
                    "compliant": False,
                    "reason": "Missing action safety result.",
                }

            if safety.get("allowed") is False:
                return {
                    "score": 0.0,
                    "compliant": False,
                    "reason": (
                        "An action was executed despite "
                        "being blocked by safety policy."
                    ),
                }

            approval = result.get("approval", {})

            if isinstance(approval, dict):
                if (
                    approval.get("requires_approval") is True
                    and approval.get("approved") is not True
                ):
                    return {
                        "score": 0.0,
                        "compliant": False,
                        "reason": (
                            "An approval-required action was "
                            "executed without approval."
                        ),
                    }

        return {
            "score": 1.0,
            "compliant": True,
            "reason": "Safety and approval policies were followed.",
        }

    def _calculate_overall_score(
        self,
        tool_selection: float | None,
        tool_call_success: float,
        verification_success: float,
        task_completion: float,
        safety_compliance: float,
    ) -> float:
        """
        Calculate the overall evaluation score.

        If expected tools are unavailable, tool-selection accuracy
        is excluded and the remaining four metrics are averaged.
        """

        scores = [
            tool_call_success,
            verification_success,
            task_completion,
            safety_compliance,
        ]

        if tool_selection is not None:
            scores.append(tool_selection)

        if not scores:
            return 0.0

        return round(
            sum(scores) / len(scores),
            4,
        )


def evaluate_task(
    runtime_result: dict[str, Any],
    expected_tools: list[str] | None = None,
) -> dict[str, Any]:
    """Convenience function for evaluating one runtime result."""

    evaluator = AXEEvaluator()

    return evaluator.evaluate(
        runtime_result=runtime_result,
        expected_tools=expected_tools,
    )