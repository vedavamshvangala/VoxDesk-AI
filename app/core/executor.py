from typing import Any, Callable

from app.core.task import Action


class TaskExecutor:
    """
    Executes approved AXE actions through a controlled tool registry.

    The executor does not execute arbitrary Python code or operating
    system commands. Every action must map to a registered tool.
    """

    def __init__(self) -> None:
        self.tools: dict[str, Callable[..., Any]] = {}

    def register_tool(
        self,
        name: str,
        function: Callable[..., Any],
    ) -> None:
        """
        Register an approved tool that AXE is allowed to execute.
        """

        if not name or not name.strip():
            raise ValueError("Tool name cannot be empty.")

        if not callable(function):
            raise TypeError("Tool must be callable.")

        self.tools[name.strip()] = function

    def execute_action(self, action: Action) -> dict[str, Any]:
        """
        Execute one approved AXE action.
        """

        if not isinstance(action, Action):
            return {
                "success": False,
                "tool": None,
                "message": "Invalid action.",
            }

        tool_name = action.tool.strip()

        if not tool_name:
            return {
                "success": False,
                "tool": None,
                "message": "Action does not specify a tool.",
            }

        if tool_name not in self.tools:
            return {
                "success": False,
                "tool": tool_name,
                "message": (
                    f"Tool '{tool_name}' is not registered "
                    "with AXE."
                ),
            }

        tool = self.tools[tool_name]

        try:
            result = tool(**action.arguments)

            if isinstance(result, dict):
                return {
                    "success": result.get("success", False),
                    "tool": tool_name,
                    "result": result,
                    "message": result.get(
                        "message",
                        "Tool execution completed.",
                    ),
                }

            return {
                "success": True,
                "tool": tool_name,
                "result": result,
                "message": "Tool execution completed.",
            }

        except Exception as exc:
            return {
                "success": False,
                "tool": tool_name,
                "result": None,
                "message": (
                    f"Tool '{tool_name}' failed: {exc}"
                ),
            }

    def execute_task(self, actions: list[Action]) -> dict[str, Any]:
        """
        Execute a sequence of actions in order.

        Execution stops immediately when an action fails.
        """

        results = []

        for index, action in enumerate(actions, start=1):
            result = self.execute_action(action)

            results.append(
                {
                    "step": index,
                    **result,
                }
            )

            if not result["success"]:
                return {
                    "success": False,
                    "completed_steps": index - 1,
                    "total_steps": len(actions),
                    "results": results,
                    "message": (
                        f"Task stopped at step {index} "
                        f"because tool '{action.tool}' failed."
                    ),
                }

        return {
            "success": True,
            "completed_steps": len(actions),
            "total_steps": len(actions),
            "results": results,
            "message": "Task completed successfully.",
        }