from app.evaluation.evaluator import AXEEvaluator


def test_perfect_task_evaluation():
    evaluator = AXEEvaluator()

    runtime_result = {
        "success": True,
        "verified": True,
        "completed_steps": 2,
        "total_steps": 2,
        "results": [
            {
                "tool": "open_application",
                "success": True,
                "verified": True,
                "safety": {
                    "allowed": True,
                },
                "approval": {
                    "approved": True,
                    "requires_approval": False,
                },
            },
            {
                "tool": "type_text",
                "success": True,
                "verified": True,
                "safety": {
                    "allowed": True,
                },
                "approval": {
                    "approved": True,
                    "requires_approval": False,
                },
            },
        ],
        "safety": {
            "allowed": True,
        },
    }

    result = evaluator.evaluate(
        runtime_result,
        expected_tools=[
            "open_application",
            "type_text",
        ],
    )

    metrics = result["metrics"]

    assert metrics["tool_selection_accuracy"] == 1.0
    assert metrics["tool_call_success_rate"] == 1.0
    assert metrics["verification_success_rate"] == 1.0
    assert metrics["task_completion_rate"] == 1.0
    assert metrics["safety_compliance"] == 1.0
    assert metrics["overall_score"] == 1.0


def test_failed_tool_call_is_detected():
    evaluator = AXEEvaluator()

    runtime_result = {
        "success": False,
        "verified": False,
        "completed_steps": 0,
        "total_steps": 1,
        "results": [
            {
                "tool": "open_application",
                "success": False,
                "verified": False,
                "safety": {
                    "allowed": True,
                },
                "approval": {
                    "approved": True,
                    "requires_approval": False,
                },
            }
        ],
        "safety": {
            "allowed": True,
        },
    }

    result = evaluator.evaluate(
        runtime_result,
        expected_tools=[
            "open_application",
        ],
    )

    metrics = result["metrics"]

    assert metrics["tool_selection_accuracy"] == 1.0
    assert metrics["tool_call_success_rate"] == 0.0
    assert metrics["verification_success_rate"] == 0.0
    assert metrics["task_completion_rate"] == 0.0