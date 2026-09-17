from app.core.planner import AXEPlanner


def test_open_notepad():
    planner = AXEPlanner()

    task = planner.plan("Open Notepad")

    assert task.actions[0].tool == "open_application"
    assert task.actions[0].arguments["application"] == "notepad"


def test_close_notepad():
    planner = AXEPlanner()

    task = planner.plan("Close Notepad")

    assert task.actions[0].tool == "close_application"
    assert task.actions[0].arguments["application"] == "notepad"


def test_multi_step_command():
    planner = AXEPlanner()

    task = planner.plan(
        "Open Notepad and write Hello AXE"
    )

    tools = [
        action.tool
        for action in task.actions
    ]

    assert tools == [
        "open_application",
        "type_text",
    ]