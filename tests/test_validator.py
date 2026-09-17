from app.core.task import Action, Task
from app.core.validator import AXEValidator


def test_valid_open_application():
    validator = AXEValidator()

    task = Task(
        intent="open_application",
        actions=[
            Action(
                tool="open_application",
                arguments={
                    "application": "notepad",
                },
            )
        ],
    )

    result = validator.validate_task(task)

    assert result["valid"] is True


def test_valid_close_application():
    validator = AXEValidator()

    task = Task(
        intent="close_application",
        actions=[
            Action(
                tool="close_application",
                arguments={
                    "application": "notepad",
                },
            )
        ],
    )

    result = validator.validate_task(task)

    assert result["valid"] is True


def test_unknown_application_rejected():
    validator = AXEValidator()

    task = Task(
        intent="open_application",
        actions=[
            Action(
                tool="open_application",
                arguments={
                    "application": "unknown_app",
                },
            )
        ],
    )

    result = validator.validate_task(task)

    assert result["valid"] is False