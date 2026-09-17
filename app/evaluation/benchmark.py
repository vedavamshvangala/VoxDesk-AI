"""AXE benchmark runner."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.agent import AXE
from app.evaluation.evaluator import AXEEvaluator


@dataclass
class BenchmarkCase:
    """One AXE evaluation test case."""

    name: str
    command: str
    expected_tools: list[str]


class AXEBenchmark:
    """Run a collection of AXE tasks and aggregate their metrics."""

    def __init__(self) -> None:
        self.agent = AXE()
        self.evaluator = AXEEvaluator()

    def run_case(
        self,
        case: BenchmarkCase,
    ) -> dict[str, Any]:
        """Run and evaluate one benchmark case."""

        try:
            task = self.agent.planner.plan(case.command)

            runtime_result = self.agent.runtime.execute_task(task)

            evaluation = self.evaluator.evaluate(
                runtime_result=runtime_result,
                expected_tools=case.expected_tools,
            )

            metrics = evaluation.get("metrics", {})

            passed = (
                runtime_result.get("success") is True
                and runtime_result.get("verified") is True
            )

            return {
                "name": case.name,
                "command": case.command,
                "expected_tools": case.expected_tools,
                "actual_tools": evaluation.get(
                    "execution",
                    {},
                ).get(
                    "actual_tools",
                    [],
                ),
                "passed": passed,
                "metrics": metrics,
                "runtime_result": runtime_result,
            }

        except Exception as exc:
            return {
                "name": case.name,
                "command": case.command,
                "expected_tools": case.expected_tools,
                "actual_tools": [],
                "passed": False,
                "metrics": {},
                "runtime_result": {
                    "success": False,
                    "verified": False,
                    "message": str(exc),
                },
            }

    def run(
        self,
        cases: list[BenchmarkCase],
    ) -> dict[str, Any]:
        """Run all benchmark cases and calculate aggregate metrics."""

        results = [
            self.run_case(case)
            for case in cases
        ]

        passed = sum(
            1
            for result in results
            if result["passed"]
        )

        failed = len(results) - passed

        aggregate_metrics = self._aggregate_metrics(
            results
        )

        return {
            "total_cases": len(results),
            "passed": passed,
            "failed": failed,
            "pass_rate": (
                passed / len(results)
                if results
                else 0.0
            ),
            "metrics": aggregate_metrics,
            "results": results,
        }

    def _aggregate_metrics(
        self,
        results: list[dict[str, Any]],
    ) -> dict[str, float]:
        """Calculate average metric scores across benchmark cases."""

        metric_names = [
            "tool_selection_accuracy",
            "tool_call_success_rate",
            "verification_success_rate",
            "task_completion_rate",
            "safety_compliance",
            "overall_score",
        ]

        aggregate: dict[str, float] = {}

        for metric_name in metric_names:
            values = []

            for result in results:
                value = result.get(
                    "metrics",
                    {},
                ).get(metric_name)

                if isinstance(value, (int, float)):
                    values.append(float(value))

            aggregate[metric_name] = round(
                sum(values) / len(values)
                if values
                else 0.0,
                4,
            )

        return aggregate


def get_default_cases() -> list[BenchmarkCase]:
    """Return the default AXE benchmark suite."""

    return [
        BenchmarkCase(
            name="Open Notepad",
            command="Open Notepad",
            expected_tools=[
                "open_application",
            ],
        ),
        BenchmarkCase(
            name="Open Calculator",
            command="Open Calculator",
            expected_tools=[
                "open_application",
            ],
        ),
        BenchmarkCase(
            name="Open and Type",
            command="Open Notepad and write Hello AXE",
            expected_tools=[
                "open_application",
                "type_text",
            ],
        ),
        BenchmarkCase(
            name="Open, Type and Backspace",
            command=(
                "Open Notepad and write ABCDE "
                "and press Backspace"
            ),
            expected_tools=[
                "open_application",
                "type_text",
                "press_key",
            ],
        ),
    ]


def print_report(
    benchmark_result: dict[str, Any],
) -> None:
    """Print a human-readable benchmark report."""

    print()
    print("=" * 60)
    print("AXE EVALUATION BENCHMARK")
    print("=" * 60)

    print()
    print(
        f"Test Cases : {benchmark_result['total_cases']}"
    )
    print(
        f"Passed     : {benchmark_result['passed']}"
    )
    print(
        f"Failed     : {benchmark_result['failed']}"
    )
    print(
        f"Pass Rate  : "
        f"{benchmark_result['pass_rate'] * 100:.2f}%"
    )

    print()
    print("-" * 60)
    print("AGGREGATE METRICS")
    print("-" * 60)

    metrics = benchmark_result.get(
        "metrics",
        {},
    )

    labels = {
        "tool_selection_accuracy":
            "Tool Selection Accuracy",
        "tool_call_success_rate":
            "Tool Call Success Rate",
        "verification_success_rate":
            "Verification Success Rate",
        "task_completion_rate":
            "Task Completion Rate",
        "safety_compliance":
            "Safety Compliance",
        "overall_score":
            "Overall Score",
    }

    for metric_name, label in labels.items():
        value = metrics.get(
            metric_name,
            0.0,
        )

        print(
            f"{label:<30}: "
            f"{value * 100:.2f}%"
        )

    print()
    print("-" * 60)
    print("TEST CASE RESULTS")
    print("-" * 60)

    for index, result in enumerate(
        benchmark_result.get("results", []),
        start=1,
    ):
        status = (
            "PASS"
            if result["passed"]
            else "FAIL"
        )

        overall = result.get(
            "metrics",
            {},
        ).get(
            "overall_score",
            0.0,
        )

        print(
            f"{index}. "
            f"{result['name']:<32} "
            f"{status:<6} "
            f"{overall * 100:.2f}%"
        )

    print()
    print("=" * 60)


def main() -> None:
    """Run the default AXE benchmark."""

    benchmark = AXEBenchmark()

    cases = get_default_cases()

    result = benchmark.run(cases)

    print_report(result)


if __name__ == "__main__":
    main()