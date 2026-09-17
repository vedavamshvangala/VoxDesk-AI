from dataclasses import dataclass, field
from typing import Any


@dataclass
class Action:
    """
    Represents one executable action in an AXE task.
    """

    tool: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class Task:
    """
    Represents a complete task requested by the user.

    A task can contain one or more ordered actions.
    """

    intent: str
    actions: list[Action] = field(default_factory=list)