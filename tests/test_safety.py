from app.core.safety import AXESafetyEngine
from app.core.task import Action


def test_open_application_is_safe():
    safety = AXESafetyEngine()

    action = Action(
        tool="open_application",
        arguments={
            "application": "notepad",
        },
    )

    result = safety.classify_action(action)

    assert result["safe"] is True
    assert result["risk_level"] == "safe"
    assert result["requires_approval"] is False
    assert result["allowed"] is True


def test_close_application_requires_approval():
    safety = AXESafetyEngine()

    action = Action(
        tool="close_application",
        arguments={
            "application": "notepad",
        },
    )

    result = safety.classify_action(action)

    assert result["safe"] is False
    assert result["risk_level"] == "medium"
    assert result["requires_approval"] is True
    assert result["allowed"] is True


def test_unknown_tool_is_blocked():
    safety = AXESafetyEngine()

    action = Action(
        tool="unknown_tool",
        arguments={},
    )

    result = safety.classify_action(action)

    assert result["safe"] is False
    assert result["risk_level"] == "critical"
    assert result["allowed"] is False