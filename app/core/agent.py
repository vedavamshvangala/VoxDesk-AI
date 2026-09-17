"""AXE conversational agent core."""

from dotenv import load_dotenv

from app.core.planner import AXEPlanner
from app.core.runtime import AXERuntime
from app.core.validator import AXEValidator


class AXE:
    """
    AXE - Autonomous eXecution Engine.

    AXE receives a natural-language request, creates a structured
    task through the planner, validates the task, and executes
    only validated tasks through AXE Runtime.

    Medium/high-risk tasks may require explicit human approval
    before execution.
    """

    NAME = "AXE"

    APPLICATION_DISPLAY_NAMES = {
        "notepad": "Notepad",
        "calculator": "Calculator",
        "file_explorer": "File Explorer",
        "paint": "Paint",
        "command_prompt": "Command Prompt",
        "vscode": "VS Code",
    }

    APPROVAL_YES_RESPONSES = {
        "yes",
        "y",
        "yeah",
        "yep",
        "yup",
        "sure",
        "okay",
        "ok",
        "alright",
        "all right",
        "go ahead",
        "do it",
        "continue",
        "proceed",
        "approve",
        "approved",
    }

    APPROVAL_NO_RESPONSES = {
        "no",
        "n",
        "nope",
        "nah",
        "cancel",
        "stop",
        "reject",
        "rejected",
        "don't",
        "dont",
        "do not",
    }

    def __init__(self) -> None:
        load_dotenv()

        self.session_active = True

        self.planner = AXEPlanner()
        self.validator = AXEValidator()
        self.runtime = AXERuntime()

        # Stores a task that is waiting for human approval.
        self.pending_task = None

    def respond(self, message: str) -> str:
        """
        Process a natural-language user request.

        This method intentionally continues returning a string so
        existing AXE callers and tests remain compatible.
        """

        if not message or not message.strip():
            return "I didn't receive a command."

        command = message.strip().lower()

        # ---------------------------------------------------------
        # Handle pending approval first
        # ---------------------------------------------------------

        if self.pending_task is not None:
            approval_response = self._handle_pending_approval(
                command
            )

            if approval_response is not None:
                return approval_response

        # ---------------------------------------------------------
        # Basic conversation
        # ---------------------------------------------------------

        if command in {
            "hi",
            "hello",
            "hey",
            "hi axe",
            "hello axe",
            "hey axe",
        }:
            return "Hello. I am AXE."

        if command in {
            "who are you",
            "who are u",
            "what is your name",
            "what is ur name",
            "what is u r name",
            "whats your name",
            "whats ur name",
            "your name",
            "tell me your name",
        }:
            return (
                "I am AXE, the Autonomous eXecution Engine."
            )

        if command in {
            "what can you do",
            "what can u do",
            "what can you do for me",
            "what do you do",
            "what do u do",
            "your capabilities",
            "tell me what you can do",
            "tell me your capabilities",
            "help",
        }:
            return (
                "I can understand natural-language commands "
                "and execute supported desktop tasks."
            )

        if command in {
            "thank you",
            "thankyou",
            "thanks",
            "thank u",
            "thx",
            "ty",
        }:
            return "You're welcome."

        if command in {
            "ok",
            "okay",
            "got it",
            "alright",
            "all right",
            "good",
            "great",
        }:
            return "You're welcome. I'm ready when you are."

        # ---------------------------------------------------------
        # Planning
        # ---------------------------------------------------------

        try:
            task = self.planner.plan(message)

        except ValueError as exc:
            return (
                "I could not create a valid plan for that request. "
                f"{exc}"
            )

        except Exception as exc:
            return (
                "I encountered an error while understanding "
                f"your request: {exc}"
            )

        # ---------------------------------------------------------
        # Validation
        # ---------------------------------------------------------

        validation = self.validator.validate_task(task)

        if not validation["valid"]:
            errors = validation.get("errors", [])

            if errors:
                return (
                    "I cannot execute that request because "
                    "the planned actions failed safety validation. "
                    f"{' '.join(errors)}"
                )

            return (
                "I cannot execute that request because "
                "the planned actions failed safety validation."
            )

        # ---------------------------------------------------------
        # Execution
        # ---------------------------------------------------------

        return self._execute_task(task)

    def respond_structured(
        self,
        message: str,
    ) -> dict:
        """
        Process a request and return a structured AXE response.

        This method is designed for the voice layer and future
        UI/API integrations.

        Existing respond() behavior remains unchanged.
        """

        if not message or not message.strip():
            return {
                "success": False,
                "status": "not_understood",
                "message": (
                    "I didn't receive a command. "
                    "Please repeat it."
                ),
            }

        command = message.strip()

        # ---------------------------------------------------------
        # Pending approval
        # ---------------------------------------------------------

        if self.pending_task is not None:
            normalized_command = command.lower()

            if normalized_command in self.APPROVAL_YES_RESPONSES:
                response = self.respond(command)

                if self.pending_task is None:
                    return {
                        "success": True,
                        "status": "completed",
                        "message": response,
                    }

                return {
                    "success": False,
                    "status": "execution_failed",
                    "message": response,
                }

            if normalized_command in self.APPROVAL_NO_RESPONSES:
                response = self.respond(command)

                return {
                    "success": True,
                    "status": "cancelled",
                    "message": response,
                }

            response = self.respond(command)

            return {
                "success": False,
                "status": "approval_required",
                "message": response,
            }

        # ---------------------------------------------------------
        # Conversation
        # ---------------------------------------------------------

        normalized_command = command.lower()

        if normalized_command in {
            "hi",
            "hello",
            "hey",
            "hi axe",
            "hello axe",
            "hey axe",
            "who are you",
            "who are u",
            "what is your name",
            "what is ur name",
            "what is u r name",
            "whats your name",
            "whats ur name",
            "your name",
            "tell me your name",
            "what can you do",
            "what can u do",
            "what can you do for me",
            "what do you do",
            "what do u do",
            "your capabilities",
            "tell me what you can do",
            "tell me your capabilities",
            "help",
            "thank you",
            "thankyou",
            "thanks",
            "thank u",
            "thx",
            "ty",
            "ok",
            "okay",
            "got it",
            "alright",
            "all right",
            "good",
            "great",
        }:
            response = self.respond(command)

            return {
                "success": True,
                "status": "conversation",
                "message": response,
            }

        # ---------------------------------------------------------
        # Planning
        # ---------------------------------------------------------

        try:
            task = self.planner.plan(command)

        except ValueError as exc:
            error_text = str(exc)

            if self._is_not_understood_error(error_text):
                return {
                    "success": False,
                    "status": "not_understood",
                    "message": (
                        "I couldn't understand that request. "
                        "Please repeat it."
                    ),
                    "error": error_text,
                }

            return {
                "success": False,
                "status": "not_understood",
                "message": (
                    "I couldn't understand that request. "
                    "Please repeat it."
                ),
                "error": error_text,
            }

        except Exception as exc:
            return {
                "success": False,
                "status": "not_understood",
                "message": (
                    "I had trouble understanding that request. "
                    "Please repeat it."
                ),
                "error": str(exc),
            }

        # ---------------------------------------------------------
        # Empty / invalid task
        # ---------------------------------------------------------

        if not task.actions:
            return {
                "success": False,
                "status": "not_understood",
                "message": (
                    "I couldn't understand that request. "
                    "Please repeat it."
                ),
            }

        # ---------------------------------------------------------
        # Validation
        # ---------------------------------------------------------

        validation = self.validator.validate_task(task)

        if not validation["valid"]:
            errors = validation.get("errors", [])

            return {
                "success": False,
                "status": "blocked",
                "message": (
                    "I cannot execute that request because "
                    "the planned actions failed safety validation."
                ),
                "errors": errors,
            }

        # ---------------------------------------------------------
        # Execution
        # ---------------------------------------------------------

        result = self.runtime.execute_task(task)

        approval = result.get("approval", {})

        if (
            not result["success"]
            and approval.get("decision") == "approval_required"
        ):
            self.pending_task = task

            response = self._generate_approval_request(
                task,
                result,
            )

            return {
                "success": False,
                "status": "approval_required",
                "message": response,
                "risk_level": approval.get(
                    "risk_level",
                    "medium",
                ),
            }

        if not result["success"]:
            self.pending_task = None

            response = self._generate_failure_response(
                result
            )

            return {
                "success": False,
                "status": "execution_failed",
                "message": response,
                "result": result,
            }

        self.pending_task = None

        response = self._generate_success_response(
            task,
            result,
        )

        return {
            "success": True,
            "status": "completed",
            "message": response,
            "result": result,
        }

    @staticmethod
    def _is_not_understood_error(
        error_text: str,
    ) -> bool:
        """
        Identify planner errors that indicate the user's
        request could not be converted into an executable task.
        """

        normalized = error_text.strip().lower()

        not_understood_patterns = {
            "at least one action is required",
            "no valid action",
            "no actions",
            "unable to create a plan",
            "could not create a plan",
        }

        return any(
            pattern in normalized
            for pattern in not_understood_patterns
        )

    def _execute_task(
        self,
        task,
        user_approved=None,
    ) -> str:
        """
        Execute a validated task through AXE Runtime.

        If Runtime requires human approval, the task is stored
        and execution is stopped until the user responds.
        """

        result = self.runtime.execute_task(
            task,
            user_approved=user_approved,
        )

        approval = result.get("approval", {})

        # ---------------------------------------------------------
        # Human approval required
        # ---------------------------------------------------------

        if (
            not result["success"]
            and approval.get("decision") == "approval_required"
        ):
            self.pending_task = task

            return self._generate_approval_request(
                task,
                result,
            )

        # ---------------------------------------------------------
        # Execution failed
        # ---------------------------------------------------------

        if not result["success"]:
            self.pending_task = None

            return self._generate_failure_response(
                result
            )

        # ---------------------------------------------------------
        # Execution succeeded
        # ---------------------------------------------------------

        self.pending_task = None

        return self._generate_success_response(
            task,
            result,
        )

    def _handle_pending_approval(
        self,
        command: str,
    ):
        """
        Handle the user's response to a pending approval request.

        Returns None only when the command is not recognized as
        an approval or rejection response.
        """

        if command in self.APPROVAL_YES_RESPONSES:
            task = self.pending_task

            return self._execute_approved_task(task)

        if command in self.APPROVAL_NO_RESPONSES:
            self.pending_task = None

            return (
                "Okay. I cancelled the pending action. "
                "Nothing was executed."
            )

        return (
            "I am waiting for your approval. "
            "Please say yes to continue or no to cancel."
        )

    def _execute_approved_task(
        self,
        task,
    ) -> str:
        """
        Execute a previously pending task after explicit
        human approval.
        """

        result = self.runtime.execute_task(
            task,
            user_approved=True,
        )

        self.pending_task = None

        if not result["success"]:
            return self._generate_failure_response(
                result
            )

        return self._generate_success_response(
            task,
            result,
        )

    def _generate_approval_request(
        self,
        task,
        result,
    ) -> str:
        """
        Generate a clear approval request based on the
        actual safety decision.
        """

        approval = result.get("approval", {})

        risk_level = approval.get(
            "risk_level",
            "medium",
        )

        description = self._describe_task_for_approval(
            task
        )

        return (
            f"This is a {risk_level}-risk action. "
            f"{description} "
            "This action requires your approval. "
            "Do you want me to continue?"
        )

    def _describe_task_for_approval(
        self,
        task,
    ) -> str:
        """
        Create a concise human-readable description
        of the pending task.
        """

        descriptions = []

        for action in task.actions:
            tool = action.tool

            if tool == "close_application":
                application = action.arguments.get(
                    "application"
                )

                if application:
                    display_name = (
                        self._get_application_display_name(
                            application
                        )
                    )

                    descriptions.append(
                        f"This will close {display_name}."
                    )

            elif tool == "open_application":
                application = action.arguments.get(
                    "application"
                )

                if application:
                    display_name = (
                        self._get_application_display_name(
                            application
                        )
                    )

                    descriptions.append(
                        f"This will open {display_name}."
                    )

            else:
                descriptions.append(
                    f"This will execute the "
                    f"'{tool}' action."
                )

        if descriptions:
            return " ".join(descriptions)

        return "This action may modify your desktop state."

    def _generate_success_response(
        self,
        task,
        result,
    ) -> str:
        """
        Generate a response from the actual execution result.
        """

        completed_steps = result.get(
            "completed_steps",
            0,
        )

        total_steps = result.get(
            "total_steps",
            0,
        )

        if completed_steps != total_steps:
            return (
                "The task did not complete successfully. "
                f"Completed {completed_steps} of "
                f"{total_steps} steps."
            )

        if task.intent == "open_application":
            for action in task.actions:
                if (
                    action.tool == "open_application"
                    and action.arguments.get("application")
                ):
                    application = action.arguments[
                        "application"
                    ]

                    display_name = (
                        self._get_application_display_name(
                            application
                        )
                    )

                    return (
                        f"{display_name} "
                        "is open and ready."
                    )

        if task.intent == "press_key":
            return "The key was pressed successfully."

        # Calculator results are returned by AXE Runtime inside each
        # completed action's nested result dictionary. Surface the
        # verified calculator value instead of returning only a generic
        # task-completed message.
        if task.intent == "calculate":
            for action in task.actions:
                if action.tool != "calculator":
                    continue

                for action_result in result.get("results", []):
                    if action_result.get("tool") != "calculator":
                        continue

                    tool_result = action_result.get("result")

                    if isinstance(tool_result, dict):
                        if tool_result.get("success") is False:
                            continue

                        if "result" in tool_result:
                            calculated_value = tool_result.get("result")
                            expression = tool_result.get(
                                "expression",
                                action.arguments.get("expression", ""),
                            )

                            if expression:
                                return (
                                    f"The result of {expression} is "
                                    f"{calculated_value}."
                                )

                            return f"The result is {calculated_value}."

                # Some runtime paths may expose the completed action
                # differently. Fall back to the top-level result list
                # only after checking the standard nested structure.
                for action_result in result.get("completed_actions", []):
                    if action_result.get("tool") != "calculator":
                        continue

                    tool_result = action_result.get("result")
                    if isinstance(tool_result, dict) and "result" in tool_result:
                        return f"The result is {tool_result['result']}."

        if task.intent == "desktop_task":
            return (
                "Done. I completed the requested "
                "desktop task successfully."
            )

        for action in task.actions:
            if (
                action.tool == "close_application"
                and action.arguments.get("application")
            ):
                application = action.arguments[
                    "application"
                ]

                display_name = (
                    self._get_application_display_name(
                        application
                    )
                )

                return (
                    f"{display_name} was closed "
                    "successfully."
                )

        return "The task was completed successfully."

    def _get_application_display_name(
        self,
        application: str,
    ) -> str:
        """
        Convert an internal application name into a
        user-friendly display name.
        """

        canonical_name = application.strip().lower()

        return self.APPLICATION_DISPLAY_NAMES.get(
            canonical_name,
            canonical_name.replace(
                "_",
                " ",
            ).title(),
        )

    def _generate_failure_response(
        self,
        result,
    ) -> str:
        """
        Generate a response from the actual execution failure.
        """

        completed_steps = result.get(
            "completed_steps",
            0,
        )

        total_steps = result.get(
            "total_steps",
            0,
        )

        message = result.get(
            "message",
            "The task could not be completed.",
        )

        return (
            "I could not complete the task. "
            f"{message} "
            f"Completed {completed_steps} of "
            f"{total_steps} steps."
        )