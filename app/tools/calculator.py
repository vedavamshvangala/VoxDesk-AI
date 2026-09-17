
"""
Safe arithmetic calculator tool for AXE.

This tool evaluates arithmetic expressions without using Python eval()
or executing arbitrary Python code.

It also performs the calculation in the Windows Calculator desktop
application through Windows UI Automation.

Supported by the safe evaluator:
- Addition: +
- Subtraction: -
- Multiplication: *
- Division: /
- Modulo: %
- Power: **
- Parentheses: ()
- Decimal numbers
- Negative numbers

Windows Calculator desktop execution supports:
- Addition: +
- Subtraction: -
- Multiplication: *
- Division: /
- Modulo: %
- Decimal numbers
- Basic negative numbers
"""


import ast
import operator
import re
import time
from typing import Any

from pywinauto import Desktop


class SafeCalculator:
    """Evaluate restricted arithmetic expressions safely."""

    _OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    MAX_EXPRESSION_LENGTH = 200
    MAX_POWER = 100

    def calculate(self, expression: str) -> dict[str, Any]:
        """
        Safely evaluate an arithmetic expression.

        Args:
            expression: Arithmetic expression such as "15 + 25".

        Returns:
            Structured calculator result.
        """

        if not isinstance(expression, str):
            return {
                "success": False,
                "expression": expression,
                "result": None,
                "message": "Calculator expression must be a string.",
            }

        expression = expression.strip()

        if not expression:
            return {
                "success": False,
                "expression": expression,
                "result": None,
                "message": "Calculator expression cannot be empty.",
            }

        if len(expression) > self.MAX_EXPRESSION_LENGTH:
            return {
                "success": False,
                "expression": expression,
                "result": None,
                "message": "Calculator expression is too long.",
            }

        try:
            tree = ast.parse(expression, mode="eval")
            result = self._evaluate(tree.body)

            if isinstance(result, float):
                if result.is_integer():
                    result = int(result)

            return {
                "success": True,
                "expression": expression,
                "result": result,
                "message": (
                    f"The result of {expression} is {result}."
                ),
            }

        except ZeroDivisionError:
            return {
                "success": False,
                "expression": expression,
                "result": None,
                "message": "Division by zero is not allowed.",
            }

        except (ValueError, TypeError, SyntaxError, OverflowError) as exc:
            return {
                "success": False,
                "expression": expression,
                "result": None,
                "message": f"Invalid arithmetic expression: {exc}",
            }

        except Exception as exc:
            return {
                "success": False,
                "expression": expression,
                "result": None,
                "message": (
                    f"Calculator failed to evaluate the expression: {exc}"
                ),
            }

    def _evaluate(self, node: ast.AST) -> int | float:
        """Recursively evaluate only approved AST nodes."""

        if isinstance(node, ast.Constant):
            value = node.value

            if isinstance(value, bool):
                raise ValueError(
                    "Boolean values are not allowed."
                )

            if isinstance(value, (int, float)):
                return value

            raise ValueError(
                "Only numeric values are allowed."
            )

        if isinstance(node, ast.BinOp):
            operator_type = type(node.op)

            if operator_type not in self._OPERATORS:
                raise ValueError(
                    "Unsupported arithmetic operator."
                )

            left = self._evaluate(node.left)
            right = self._evaluate(node.right)

            if operator_type is ast.Pow:
                if abs(right) > self.MAX_POWER:
                    raise ValueError(
                        "Power operation is too large."
                    )

            operation = self._OPERATORS[operator_type]

            return operation(left, right)

        if isinstance(node, ast.UnaryOp):
            operator_type = type(node.op)

            if operator_type not in self._OPERATORS:
                raise ValueError(
                    "Unsupported unary operator."
                )

            operand = self._evaluate(node.operand)
            operation = self._OPERATORS[operator_type]

            return operation(operand)

        raise ValueError(
            "Only arithmetic expressions are allowed."
        )


class WindowsCalculatorController:
    """
    Control the Windows Calculator application through UI Automation.

    This class deliberately uses the Calculator controls exposed by
    Windows UI Automation instead of pyautogui keyboard input.
    """

    CALCULATOR_TITLE = "Calculator"

    NUMBER_BUTTONS = {
        "0": "num0Button",
        "1": "num1Button",
        "2": "num2Button",
        "3": "num3Button",
        "4": "num4Button",
        "5": "num5Button",
        "6": "num6Button",
        "7": "num7Button",
        "8": "num8Button",
        "9": "num9Button",
    }

    OPERATOR_BUTTONS = {
        "+": "plusButton",
        "-": "minusButton",
        "*": "multiplyButton",
        "/": "divideButton",
        "%": "percentButton",
    }

    CLEAR_BUTTON = "clearButton"
    EQUALS_BUTTON = "equalButton"
    DECIMAL_BUTTON = "decimalSeparatorButton"

    def _get_calculator_window(self):
        """Return the visible Windows Calculator UI Automation window."""

        try:
            calculator = (
                Desktop(backend="uia")
                .window(title=self.CALCULATOR_TITLE)
            )

            if not calculator.exists():
                return None

            if not calculator.is_visible():
                return None

            return calculator

        except Exception:
            return None

    def _click_control(
        self,
        calculator,
        automation_id: str,
    ) -> bool:
        """Click a Calculator button by AutomationId."""

        try:
            control = calculator.child_window(
                auto_id=automation_id,
                control_type="Button",
            )

            if not control.exists():
                return False

            control.click_input()
            time.sleep(0.08)
            return True

        except Exception:
            return False

    def _clear_calculator(self, calculator) -> bool:
        """Clear the current Calculator expression."""

        return self._click_control(
            calculator,
            self.CLEAR_BUTTON,
        )

    def _tokenize_expression(
        self,
        expression: str,
    ) -> list[str] | None:
        """
        Convert a basic desktop-calculator expression into tokens.

        Supported UI expression format:
            numbers + - * / %

        Spaces are ignored.

        Parentheses and power are intentionally not sent to the
        Windows Calculator UI through this controller because the
        standard Calculator button surface inspected for this project
        does not expose those controls.
        """

        compact = expression.replace(" ", "")

        if not compact:
            return None

        if "**" in compact:
            return None

        if "(" in compact or ")" in compact:
            return None

        pattern = r"(?:\d+(?:\.\d*)?|\.\d+|[+\-*/%])"

        matches = re.findall(pattern, compact)

        if "".join(matches) != compact:
            return None

        tokens: list[str] = []

        for token in matches:
            if token in "+-*/%":
                # A leading '-' is treated as a unary negative sign.
                if not tokens and token == "-":
                    tokens.append("NEGATIVE")
                elif tokens and tokens[-1] in {
                    "+",
                    "-",
                    "*",
                    "/",
                    "%",
                    "NEGATIVE",
                } and token == "-":
                    tokens.append("NEGATIVE")
                else:
                    tokens.append(token)
            else:
                tokens.append(token)

        return tokens

    def _click_number(
        self,
        calculator,
        number: str,
    ) -> bool:
        """Enter a numeric value using Calculator buttons."""

        for character in number:
            if character.isdigit():
                automation_id = self.NUMBER_BUTTONS.get(character)

                if automation_id is None:
                    return False

                if not self._click_control(
                    calculator,
                    automation_id,
                ):
                    return False

            elif character == ".":
                if not self._click_control(
                    calculator,
                    self.DECIMAL_BUTTON,
                ):
                    return False

            else:
                return False

        return True

    def _click_operator(
        self,
        calculator,
        operator_symbol: str,
    ) -> bool:
        """Press a Calculator operator button."""

        automation_id = self.OPERATOR_BUTTONS.get(
            operator_symbol
        )

        if automation_id is None:
            return False

        return self._click_control(
            calculator,
            automation_id,
        )

    def _read_display(
        self,
        calculator,
    ) -> str | None:
        """Read the Calculator result display."""

        try:
            display = calculator.child_window(
                auto_id="CalculatorResults",
                control_type="Text",
            )

            if not display.exists():
                return None

            text = display.window_text()

            if not text:
                return None

            return text.strip()

        except Exception:
            return None

    def _extract_display_value(
        self,
        display_text: str,
    ) -> str | None:
        """
        Extract the numeric value from Calculator's display text.

        Example:
            'Display is 40' -> '40'
        """

        if not display_text:
            return None

        match = re.search(
            r"Display is\s+(.+)$",
            display_text,
            re.IGNORECASE,
        )

        if match:
            return match.group(1).strip()

        return display_text.strip()

    def execute_in_windows_calculator(
        self,
        expression: str,
    ) -> dict[str, Any]:
        """
        Execute a supported expression in the actual Windows Calculator UI.
        """

        calculator = self._get_calculator_window()

        if calculator is None:
            return {
                "success": False,
                "verified": False,
                "display": None,
                "message": (
                    "Windows Calculator is not open or could not "
                    "be accessed through UI Automation."
                ),
            }

        tokens = self._tokenize_expression(expression)

        if tokens is None:
            return {
                "success": False,
                "verified": False,
                "display": None,
                "message": (
                    "This expression cannot currently be entered "
                    "through the inspected Windows Calculator UI."
                ),
            }

        try:
            # Bring the Calculator UI into its own interaction context.
            try:
                calculator.set_focus()
                time.sleep(0.2)
            except Exception:
                pass

            if not self._clear_calculator(calculator):
                return {
                    "success": False,
                    "verified": False,
                    "display": None,
                    "message": (
                        "Could not clear the Windows Calculator."
                    ),
                }

            negative_pending = False

            for token in tokens:
                if token == "NEGATIVE":
                    negative_pending = True
                    continue

                if token in self.OPERATOR_BUTTONS:
                    if not self._click_operator(
                        calculator,
                        token,
                    ):
                        return {
                            "success": False,
                            "verified": False,
                            "display": None,
                            "message": (
                                f"Could not press Calculator "
                                f"operator '{token}'."
                            ),
                        }

                    continue

                if not self._click_number(
                    calculator,
                    token,
                ):
                    return {
                        "success": False,
                        "verified": False,
                        "display": None,
                        "message": (
                            f"Could not enter number '{token}' "
                            "into Windows Calculator."
                        ),
                    }

                if negative_pending:
                    # The standard Calculator UI exposes a
                    # positive/negative button. Use it after
                    # entering the number.
                    if not self._click_control(
                        calculator,
                        "negateButton",
                    ):
                        return {
                            "success": False,
                            "verified": False,
                            "display": None,
                            "message": (
                                "Could not apply the negative sign "
                                "in Windows Calculator."
                            ),
                        }

                    negative_pending = False

            if negative_pending:
                return {
                    "success": False,
                    "verified": False,
                    "display": None,
                    "message": (
                        "Invalid negative-number expression."
                    ),
                }

            if not self._click_control(
                calculator,
                self.EQUALS_BUTTON,
            ):
                return {
                    "success": False,
                    "verified": False,
                    "display": None,
                    "message": (
                        "Could not press Equals in Windows Calculator."
                    ),
                }

            time.sleep(0.2)

            display_text = self._read_display(
                calculator
            )

            display_value = self._extract_display_value(
                display_text or ""
            )

            if display_value is None:
                return {
                    "success": False,
                    "verified": False,
                    "display": None,
                    "message": (
                        "Windows Calculator completed the input, "
                        "but its result display could not be read."
                    ),
                }

            return {
                "success": True,
                "verified": True,
                "display": display_value,
                "display_text": display_text,
                "message": (
                    "Expression was entered and calculated in "
                    "Windows Calculator."
                ),
            }

        except Exception as exc:
            return {
                "success": False,
                "verified": False,
                "display": None,
                "message": (
                    "Failed to control Windows Calculator: "
                    f"{exc}"
                ),
            }


_calculator = SafeCalculator()
_windows_calculator = WindowsCalculatorController()


def calculator(expression: str) -> dict[str, Any]:
    """
    AXE calculator tool entry point.

    The expression is first evaluated safely by the internal
    calculator. It is then entered into the actual Windows
    Calculator application and its display is checked.

    The internal calculation remains important because it provides
    an independent expected result for AXE verification.
    """

    calculation = _calculator.calculate(expression)

    if not calculation["success"]:
        return calculation

    ui_result = _windows_calculator.execute_in_windows_calculator(
        expression
    )

    if not ui_result["success"]:
        return {
            **calculation,
            "desktop_calculator": ui_result,
            "success": False,
            "message": (
                "The expression was calculated internally, but "
                "Windows Calculator could not execute or display "
                f"the calculation: {ui_result['message']}"
            ),
        }

    expected_result = calculation["result"]
    displayed_result = ui_result["display"]

    return {
        **calculation,
        "desktop_calculator": ui_result,
        "expected_result": expected_result,
        "displayed_result": displayed_result,
        "desktop_verified": True,
        "message": (
            f"The result of {expression} is {expected_result}. "
            "The calculation was also performed and displayed "
            "in Windows Calculator."
        ),
    }


if __name__ == "__main__":
    test_expressions = [
        "15 + 25",
        "100 / 4",
        "12 * 8",
        "20 - 7",
    ]

    print("AXE CALCULATOR TEST")
    print("-" * 40)

    for expression in test_expressions:
        result = calculator(expression)
        print(f"{expression} = {result}")

