from app.core.approval import AXEApprovalGate


def test_safe_action_is_auto_approved():
    gate = AXEApprovalGate()

    safety_result = {
        "safe": True,
        "risk_level": "safe",
        "requires_approval": False,
        "allowed": True,
    }

    result = gate.evaluate(
        safety_result,
        user_approved=None,
    )

    assert result["approved"] is True
    assert result["requires_approval"] is False


def test_medium_risk_requires_approval():
    gate = AXEApprovalGate()

    safety_result = {
        "safe": False,
        "risk_level": "medium",
        "requires_approval": True,
        "allowed": True,
    }

    result = gate.evaluate(
        safety_result,
        user_approved=None,
    )

    assert result["approved"] is False
    assert result["requires_approval"] is True
    assert result["decision"] == "approval_required"


def test_medium_risk_approved():
    gate = AXEApprovalGate()

    safety_result = {
        "safe": False,
        "risk_level": "medium",
        "requires_approval": True,
        "allowed": True,
    }

    result = gate.evaluate(
        safety_result,
        user_approved=True,
    )

    assert result["approved"] is True
    assert result["requires_approval"] is True


def test_medium_risk_rejected():
    gate = AXEApprovalGate()

    safety_result = {
        "safe": False,
        "risk_level": "medium",
        "requires_approval": True,
        "allowed": True,
    }

    result = gate.evaluate(
        safety_result,
        user_approved=False,
    )

    assert result["approved"] is False