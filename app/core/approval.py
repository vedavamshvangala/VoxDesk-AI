"""AXE human approval gate."""

from typing import Any

from app.core.safety import RiskLevel


class AXEApprovalGate:
    """
    Controls whether an AXE action or task may proceed
    based on its safety decision.

    The approval gate does not execute actions.

    It only determines whether execution may continue.
    """

    def evaluate(
        self,
        safety_result: dict[str, Any],
        user_approved: bool | None = None,
    ) -> dict[str, Any]:
        """
        Evaluate a safety decision against an optional
        human approval response.

        Behavior:

        SAFE
            Automatically approved.

        MEDIUM / HIGH
            Requires explicit human approval.

        CRITICAL
            Blocked regardless of normal approval.
        """

        if not isinstance(safety_result, dict):
            return {
                "approved": False,
                "requires_approval": True,
                "risk_level": RiskLevel.CRITICAL.value,
                "decision": "blocked",
                "reason": (
                    "Invalid safety result. Execution is "
                    "blocked by default."
                ),
            }

        risk_level = safety_result.get(
            "risk_level"
        )

        if risk_level == RiskLevel.SAFE.value:
            return {
                "approved": True,
                "requires_approval": False,
                "risk_level": RiskLevel.SAFE.value,
                "decision": "auto_approved",
                "reason": (
                    "Action is classified as safe and may "
                    "execute automatically."
                ),
            }

        if risk_level == RiskLevel.CRITICAL.value:
            return {
                "approved": False,
                "requires_approval": True,
                "risk_level": RiskLevel.CRITICAL.value,
                "decision": "blocked",
                "reason": (
                    "Critical-risk action is blocked by the "
                    "AXE safety policy."
                ),
            }

        if risk_level in {
            RiskLevel.MEDIUM.value,
            RiskLevel.HIGH.value,
        }:
            if user_approved is None:
                return {
                    "approved": False,
                    "requires_approval": True,
                    "risk_level": risk_level,
                    "decision": "approval_required",
                    "reason": (
                        f"{risk_level.capitalize()}-risk action "
                        "requires explicit human approval."
                    ),
                }

            if user_approved is True:
                return {
                    "approved": True,
                    "requires_approval": True,
                    "risk_level": risk_level,
                    "decision": "human_approved",
                    "reason": (
                        f"Human approval received for the "
                        f"{risk_level}-risk action."
                    ),
                }

            return {
                "approved": False,
                "requires_approval": True,
                "risk_level": risk_level,
                "decision": "human_rejected",
                "reason": (
                    f"Human approval was rejected for the "
                    f"{risk_level}-risk action."
                ),
            }

        return {
            "approved": False,
            "requires_approval": True,
            "risk_level": RiskLevel.CRITICAL.value,
            "decision": "blocked",
            "reason": (
                "Unknown risk level. AXE blocks execution "
                "by default."
            ),
        }