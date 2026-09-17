"""AXE action risk classification and safety engine."""

from enum import Enum
from typing import Any

from app.core.task import Action


class RiskLevel(str, Enum):
    """
    Risk levels used by AXE to determine whether an action
    can execute automatically or requires additional approval.
    """

    SAFE = "safe"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AXESafetyEngine:
    """
    Classifies AXE actions according to their potential impact.

    The safety engine does not execute actions.

    Its responsibility is only to answer:

        "How risky is this action?"

    Execution and approval decisions will be connected later.
    """

    SAFE_TOOLS = {
        # Calculator
        "calculator",

        # Desktop tools
        "open_application",
        "focus_application",
        "verify_application",
        "type_text",
        "press_key",
        "hotkey",

        # Browser tools
        "open_browser",
        "navigate_browser",
        "verify_browser",
    }

    MEDIUM_TOOLS = {
        # Desktop
        "close_application",

        # Browser
        "close_browser",
    }

    HIGH_TOOLS: set[str] = set()

    CRITICAL_TOOLS: set[str] = set()

    def classify_action(
        self,
        action: Action,
    ) -> dict[str, Any]:
        """
        Classify one AXE action and return a structured
        safety decision.
        """

        if not isinstance(action, Action):
            return {
                "safe": False,
                "risk_level": RiskLevel.CRITICAL.value,
                "tool": None,
                "requires_approval": True,
                "allowed": False,
                "reason": "Invalid AXE action.",
            }

        tool = action.tool.strip().lower()

        if not tool:
            return {
                "safe": False,
                "risk_level": RiskLevel.CRITICAL.value,
                "tool": None,
                "requires_approval": True,
                "allowed": False,
                "reason": "Action does not specify a tool.",
            }

        if tool in self.CRITICAL_TOOLS:
            return self._decision(
                tool=tool,
                risk_level=RiskLevel.CRITICAL,
                requires_approval=True,
                allowed=False,
                reason=(
                    f"Tool '{tool}' represents a critical-risk "
                    "operation and is blocked until an explicit "
                    "safety policy is defined."
                ),
            )

        if tool in self.HIGH_TOOLS:
            return self._decision(
                tool=tool,
                risk_level=RiskLevel.HIGH,
                requires_approval=True,
                allowed=True,
                reason=(
                    f"Tool '{tool}' is high risk and requires "
                    "human approval before execution."
                ),
            )

        if tool in self.MEDIUM_TOOLS:
            return self._decision(
                tool=tool,
                risk_level=RiskLevel.MEDIUM,
                requires_approval=True,
                allowed=True,
                reason=(
                    f"Tool '{tool}' is medium risk and requires "
                    "human approval before execution."
                ),
            )

        if tool in self.SAFE_TOOLS:
            return self._decision(
                tool=tool,
                risk_level=RiskLevel.SAFE,
                requires_approval=False,
                allowed=True,
                reason=(
                    f"Tool '{tool}' is currently classified "
                    "as safe for automatic execution."
                ),
            )

        return self._decision(
            tool=tool,
            risk_level=RiskLevel.CRITICAL,
            requires_approval=True,
            allowed=False,
            reason=(
                f"Tool '{tool}' is not recognized by the AXE "
                "safety policy and is blocked by default."
            ),
        )

    def classify_task(
        self,
        actions: list[Action],
    ) -> dict[str, Any]:
        """
        Classify every action in a task.

        The task receives the highest risk level among its
        actions.

        An unknown or critical action causes the task to be
        blocked.

        Medium/high actions require approval.
        """

        if not isinstance(actions, list):
            return {
                "safe": False,
                "risk_level": RiskLevel.CRITICAL.value,
                "requires_approval": True,
                "allowed": False,
                "results": [],
                "reason": "Task actions must be a list.",
            }

        if not actions:
            return {
                "safe": False,
                "risk_level": RiskLevel.CRITICAL.value,
                "requires_approval": True,
                "allowed": False,
                "results": [],
                "reason": "Task contains no actions.",
            }

        results: list[dict[str, Any]] = []

        for action in actions:
            result = self.classify_action(action)
            results.append(result)

        risk_priority = {
            RiskLevel.SAFE.value: 0,
            RiskLevel.MEDIUM.value: 1,
            RiskLevel.HIGH.value: 2,
            RiskLevel.CRITICAL.value: 3,
        }

        highest_risk = max(
            results,
            key=lambda result: risk_priority.get(
                result["risk_level"],
                3,
            ),
        )

        highest_risk_level = highest_risk["risk_level"]

        if highest_risk_level == RiskLevel.CRITICAL.value:
            return {
                "safe": False,
                "risk_level": RiskLevel.CRITICAL.value,
                "requires_approval": True,
                "allowed": False,
                "results": results,
                "reason": (
                    "Task contains a critical or unknown-risk "
                    "action and is blocked."
                ),
            }

        if highest_risk_level in {
            RiskLevel.HIGH.value,
            RiskLevel.MEDIUM.value,
        }:
            return {
                "safe": False,
                "risk_level": highest_risk_level,
                "requires_approval": True,
                "allowed": True,
                "results": results,
                "reason": (
                    f"Task contains {highest_risk_level}-risk "
                    "actions and requires human approval "
                    "before execution."
                ),
            }

        return {
            "safe": True,
            "risk_level": RiskLevel.SAFE.value,
            "requires_approval": False,
            "allowed": True,
            "results": results,
            "reason": (
                "All task actions are currently classified "
                "as safe for automatic execution."
            ),
        }

    def _decision(
        self,
        tool: str,
        risk_level: RiskLevel,
        requires_approval: bool,
        allowed: bool,
        reason: str,
    ) -> dict[str, Any]:
        """
        Create a consistent safety decision.
        """

        return {
            "safe": risk_level == RiskLevel.SAFE,
            "risk_level": risk_level.value,
            "tool": tool,
            "requires_approval": requires_approval,
            "allowed": allowed,
            "reason": reason,
        }