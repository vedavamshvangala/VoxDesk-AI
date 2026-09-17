"""AXE natural-language task planner."""

import json
import os
import re

from langchain_groq import ChatGroq

from app.core.task import Action, Task
from app.tools.applications import get_allowed_applications


class AXEPlanner:
    """
    Converts natural-language user requests into structured AXE tasks.

    The planner is responsible only for understanding the request
    and producing a safe, structured plan.

    It does NOT execute tools.
    """

    ALLOWED_TOOLS = {
        "open_application",
        "focus_application",
        "close_application",
        "type_text",
        "press_key",
        "hotkey",
        "verify_application",
        "open_browser",
        "navigate_browser",
        "verify_browser",
        "close_browser",
        "calculator",
    }

    _CALCULATOR_PATTERN = re.compile(
        r"^\s*(?:what\s+is\s+|calculate\s+|compute\s+|solve\s+)?"
        r"(?P<expression>[\d\s+\-*/%().]+)"
        r"\s*\??\s*$",
        re.IGNORECASE,
    )

    _WORD_NUMBER_MAP = {
        "zero": "0",
        "one": "1",
        "two": "2",
        "three": "3",
        "four": "4",
        "five": "5",
        "six": "6",
        "seven": "7",
        "eight": "8",
        "nine": "9",
        "ten": "10",
        "eleven": "11",
        "twelve": "12",
        "thirteen": "13",
        "fourteen": "14",
        "fifteen": "15",
        "sixteen": "16",
        "seventeen": "17",
        "eighteen": "18",
        "nineteen": "19",
        "twenty": "20",
        "thirty": "30",
        "forty": "40",
        "fifty": "50",
        "sixty": "60",
        "seventy": "70",
        "eighty": "80",
        "ninety": "90",
        "hundred": "100",
    }

    _CALCULATOR_WORD_PATTERN = re.compile(
        r"^\s*(?:what\s+is\s+|calculate\s+|compute\s+|solve\s+)?"
        r"(?P<left>[a-z]+|\d+(?:\.\d+)?)\s+"
        r"(?P<operator>plus|add|minus|subtract|times|multiplied\s+by|"
        r"divided\s+by|divide|modulo|mod|%)\s+"
        r"(?P<right>[a-z]+|\d+(?:\.\d+)?)"
        r"\s*\??\s*$",
        re.IGNORECASE,
    )

    def __init__(
        self,
        model: str = "openai/gpt-oss-20b",
        temperature: float = 0.0,
    ) -> None:
        """Initialize the Groq-based planner."""

        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise ValueError(
                "GROQ_API_KEY environment variable is not set."
            )

        self.llm = ChatGroq(
            model=model,
            temperature=temperature,
            api_key=api_key,
        )

    def plan(self, user_input: str) -> Task:
        """Convert a natural-language user request into an AXE Task."""

        if not user_input or not user_input.strip():
            raise ValueError("User input cannot be empty.")

        normalized_input = user_input.strip()

        calculator_task = self._try_build_calculator_task(
            normalized_input
        )

        if calculator_task is not None:
            return calculator_task

        # Preserve unknown application requests as a real action so the
        # validator/runtime can report the actual unsupported application
        # instead of treating the request as an empty task.
        open_app_task = self._try_build_open_application_task(
            normalized_input
        )

        if open_app_task is not None:
            return open_app_task

        prompt = self._build_prompt(normalized_input)

        response = self.llm.invoke(prompt)
        content = response.content

        if not isinstance(content, str):
            raise ValueError(
                "Planner returned an unexpected response format."
            )

        return self._parse_task(content)

    def _try_build_open_application_task(
        self,
        user_input: str,
    ) -> Task | None:
        """Preserve explicit open-application requests for downstream validation."""

        match = re.match(
            r"^\s*open\s+(?:an?\s+)?application\s+called\s+(.+?)\s*$",
            user_input,
            re.IGNORECASE,
        )

        if not match:
            return None

        application = match.group(1).strip().strip('"').strip("'")

        if not application:
            return None

        return Task(
            intent="open_application",
            actions=[
                Action(
                    tool="open_application",
                    arguments={"application": application},
                )
            ],
        )

    def _try_build_calculator_task(
        self,
        user_input: str,
    ) -> Task | None:
        """
        Detect simple arithmetic requests deterministically.

        This prevents a straightforward arithmetic request from
        depending on the LLM to remember that the calculator tool
        exists.
        """

        match = self._CALCULATOR_PATTERN.match(user_input)

        if match:
            expression = match.group("expression").strip()

            if expression:
                return Task(
                    intent="calculate",
                    actions=[
                        Action(
                            tool="calculator",
                            arguments={
                                "expression": expression,
                            },
                        )
                    ],
                )

        word_match = self._CALCULATOR_WORD_PATTERN.match(user_input)

        if not word_match:
            return None

        left = self._normalize_number_token(
            word_match.group("left")
        )
        right = self._normalize_number_token(
            word_match.group("right")
        )

        if left is None or right is None:
            return None

        operator = word_match.group("operator").lower()
        operator = " ".join(operator.split())

        operator_map = {
            "plus": "+",
            "add": "+",
            "minus": "-",
            "subtract": "-",
            "times": "*",
            "multiplied by": "*",
            "divided by": "/",
            "divide": "/",
            "modulo": "%",
            "mod": "%",
            "%": "%",
        }

        symbol = operator_map.get(operator)

        if symbol is None:
            return None

        expression = f"{left} {symbol} {right}"

        return Task(
            intent="calculate",
            actions=[
                Action(
                    tool="calculator",
                    arguments={
                        "expression": expression,
                    },
                )
            ],
        )

    def _normalize_number_token(
        self,
        token: str,
    ) -> str | None:
        """Normalize a simple number word or numeric token."""

        normalized = token.strip().lower()

        if normalized in self._WORD_NUMBER_MAP:
            return self._WORD_NUMBER_MAP[normalized]

        try:
            float(normalized)
            return normalized
        except ValueError:
            return None

    def _build_prompt(self, user_input: str) -> str:
        """Build the strict planning prompt for Groq."""

        allowed_applications = get_allowed_applications()

        applications_text = "\n".join(
            f"- {application}"
            for application in allowed_applications
        )

        return f"""
You are the planning engine for AXE
(Autonomous eXecution Engine), a Windows desktop agent.

Your job is to convert the user's natural-language request
into a structured JSON task.

You MUST NOT execute anything.

You MUST ONLY use the following tools:

1. open_application
   Arguments:
   {{
       "application": "application_name"
   }}

2. focus_application
   Arguments:
   {{
       "application": "application_name"
   }}

3. type_text
   Arguments:
   {{
       "text": "text_to_type"
   }}

4. press_key
   Arguments:
   {{
       "key": "key_name"
   }}

5. hotkey
   Arguments:
   {{
       "keys": ["key1", "key2"]
   }}

6. verify_application
   Arguments:
   {{
       "application": "application_name"
   }}

7. close_application
   Arguments:
   {{
       "application": "application_name"
   }}

8. open_browser
   Arguments:
   {{}}

9. navigate_browser
   Arguments:
   {{
       "url": "https://example.com"
   }}

10. verify_browser
    Arguments:
    {{
        "url": "https://example.com"
    }}

11. close_browser
    Arguments:
    {{}}

12. calculator
    Arguments:
    {{
        "expression": "15 + 25"
    }}

CALCULATOR RULE:

Use the calculator tool whenever the user asks you to
perform arithmetic or calculate a numerical expression.

Examples include:

    "What is 15 plus 25?"
    "Calculate 100 / 4"
    "What is 12 * 8?"
    "Compute (10 + 5) * 2"
    "What is 50 minus 17?"

Convert natural-language arithmetic operators to standard
arithmetic symbols when necessary.

Examples:

    plus -> +
    minus -> -
    times -> *
    multiplied by -> *
    divided by -> /
    divide -> /
    modulo -> %

The calculator action MUST contain exactly the arithmetic
expression in the "expression" argument.

Do NOT use open_application to open the Windows Calculator
for an arithmetic request.

Currently approved applications:

{applications_text}

Application aliases may be understood from natural language,
but the output MUST use the canonical application name
from the approved application list.

IMPORTANT PLANNING RULES:

- Return ONLY valid JSON.
- Do not use Markdown.
- Do not include explanations.
- Do not invent tools.
- Do not invent arguments.
- Do not invent applications.
- Preserve the user's intended text exactly when creating type_text.
- Actions must be ordered logically.
- Do not add unnecessary actions.
- Arithmetic requests must use calculator.
- Calculator requests must not open the Windows Calculator application.

OPEN APPLICATION RULE:

When the user only asks to open an application:

    "open notepad"
    "open calculator"
    "open paint"
    "open file explorer"
    "open vs code"

use ONLY:

    open_application

Do NOT add focus_application.

Do NOT add verify_application.

The open_application tool internally handles:

    launch
    application verification
    window focus
    focus verification

Therefore, adding separate focus_application or
verify_application actions for a simple open request
would be redundant.

INTERACTION RULE:

When the user asks to open an application AND interact
with it, use open_application followed by only the
actions required for the interaction.

For example:

    "open notepad and write hello"

should use:

    open_application
    type_text

Do NOT add focus_application because open_application
already focuses the application.

VERIFICATION RULE:

Do not add verify_application after open_application.

Verification of the application is handled internally
by open_application.

Use verify_application only when the user's request
specifically requires checking whether an application
is currently open.

KEY RULE:

For a direct key request such as:

    "press enter"

use:

    press_key

For a keyboard shortcut such as:

    "press ctrl s"

use:

    hotkey

APPLICATION RULE:

Only applications from the approved application list
may be used.

EXPECTED JSON FORMAT:

{{
    "intent": "desktop_task",
    "actions": [
        {{
            "tool": "tool_name",
            "arguments": {{}}
        }}
    ]
}}

EXAMPLES:

User:
open notepad

Output:
{{
    "intent": "open_application",
    "actions": [
        {{
            "tool": "open_application",
            "arguments": {{
                "application": "notepad"
            }}
        }}
    ]
}}

User:
open calculator

Output:
{{
    "intent": "open_application",
    "actions": [
        {{
            "tool": "open_application",
            "arguments": {{
                "application": "calculator"
            }}
        }}
    ]
}}

User:
open file explorer

Output:
{{
    "intent": "open_application",
    "actions": [
        {{
            "tool": "open_application",
            "arguments": {{
                "application": "file_explorer"
            }}
        }}
    ]
}}

User:
open paint

Output:
{{
    "intent": "open_application",
    "actions": [
        {{
            "tool": "open_application",
            "arguments": {{
                "application": "paint"
            }}
        }}
    ]
}}

User:
open command prompt

Output:
{{
    "intent": "open_application",
    "actions": [
        {{
            "tool": "open_application",
            "arguments": {{
                "application": "command_prompt"
            }}
        }}
    ]
}}

User:
open vs code

Output:
{{
    "intent": "open_application",
    "actions": [
        {{
            "tool": "open_application",
            "arguments": {{
                "application": "vscode"
            }}
        }}
    ]
}}

User:
open notepad and write hello

Output:
{{
    "intent": "desktop_task",
    "actions": [
        {{
            "tool": "open_application",
            "arguments": {{
                "application": "notepad"
            }}
        }},
        {{
            "tool": "type_text",
            "arguments": {{
                "text": "hello"
            }}
        }}
    ]
}}

User:
open note pad and write i love you

Output:
{{
    "intent": "desktop_task",
    "actions": [
        {{
            "tool": "open_application",
            "arguments": {{
                "application": "notepad"
            }}
        }},
        {{
            "tool": "type_text",
            "arguments": {{
                "text": "i love you"
            }}
        }}
    ]
}}

User:
press enter

Output:
{{
    "intent": "press_key",
    "actions": [
        {{
            "tool": "press_key",
            "arguments": {{
                "key": "enter"
            }}
        }}
    ]
}}

User:
What is 15 plus 25?

Output:
{{
    "intent": "calculate",
    "actions": [
        {{
            "tool": "calculator",
            "arguments": {{
                "expression": "15 + 25"
            }}
        }}
    ]
}}

User:
Calculate 100 / 4

Output:
{{
    "intent": "calculate",
    "actions": [
        {{
            "tool": "calculator",
            "arguments": {{
                "expression": "100 / 4"
            }}
        }}
    ]
}}

User request:
{user_input}
"""

    def _parse_task(self, content: str) -> Task:
        """Parse and validate the JSON returned by the LLM."""

        cleaned_content = content.strip()

        if cleaned_content.startswith("```"):
            lines = cleaned_content.splitlines()

            if lines and lines[0].startswith("```"):
                lines = lines[1:]

            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]

            cleaned_content = "\n".join(lines).strip()

        try:
            data = json.loads(cleaned_content)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "Planner returned invalid JSON."
            ) from exc

        if not isinstance(data, dict):
            raise ValueError(
                "Planner response must be a JSON object."
            )

        intent = data.get("intent")

        if not isinstance(intent, str) or not intent.strip():
            raise ValueError(
                "Planner response does not contain a valid intent."
            )

        raw_actions = data.get("actions")

        if not isinstance(raw_actions, list):
            raise ValueError(
                "Planner response does not contain a valid actions list."
            )

        actions: list[Action] = []

        for raw_action in raw_actions:
            if not isinstance(raw_action, dict):
                raise ValueError(
                    "Each planner action must be a JSON object."
                )

            tool = raw_action.get("tool")

            if not isinstance(tool, str) or not tool.strip():
                raise ValueError(
                    "Planner returned an action without a tool."
                )

            tool = tool.strip()

            if tool not in self.ALLOWED_TOOLS:
                raise ValueError(
                    f"Planner returned unsupported tool: {tool}"
                )

            arguments = raw_action.get("arguments", {})

            if not isinstance(arguments, dict):
                raise ValueError(
                    f"Arguments for tool '{tool}' must be an object."
                )

            actions.append(
                Action(
                    tool=tool,
                    arguments=arguments,
                )
            )

        return Task(
            intent=intent.strip(),
            actions=actions,
        )
