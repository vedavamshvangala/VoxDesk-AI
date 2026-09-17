from types import SimpleNamespace

from app.core.task import Action
from app.core.verifier import AXEVerifier
from app.tools import browser as browser_module
from app.tools import desktop


class FakePage:
    def __init__(self, url: str = "https://example.com", title: str = "Example", values: list[str] | None = None):
        self._url = url
        self._title = title
        self._values = values or [""]

    @property
    def url(self):
        return self._url

    def title(self):
        return self._title

    def evaluate(self, script):
        return self._values


class FakeEditable:
    def __init__(
        self,
        page,
        tag="input",
        visible=True,
        enabled=True,
        editable=True,
    ):
        self.page = page
        self.tag = tag
        self.visible = visible
        self.enabled = enabled
        self.editable = editable
        self.focused = False

    def is_visible(self):
        return self.visible

    def is_enabled(self):
        return self.enabled

    def is_editable(self):
        return self.editable

    def focus(self):
        self.page.focused = self
        self.focused = True

    def evaluate(self, script):
        if "activeElement" in script and "tagName" not in script:
            return self.page.focused is self
        return self.tag

    def get_attribute(self, name):
        return {
            "role": "combobox",
            "aria-label": "Search",
            "name": None,
            "placeholder": "Search",
        }.get(name)


class FakeEditableLocator:
    def __init__(self, page, elements):
        self.page = page
        self.elements = elements

    def count(self):
        return len(self.elements)

    def nth(self, index):
        return self.elements[index]


class FakeFocusLocator:
    def __init__(self, page):
        self.page = page

    def count(self):
        return 1 if self.page.focused is not None else 0


class FakeFocusPage:
    def __init__(self, elements):
        self.focused = None
        self.elements = elements

    def locator(self, selector):
        if selector == ":focus":
            return FakeFocusLocator(self)
        return FakeEditableLocator(self, self.elements)


def test_notepad_type_text_verification_succeeds(monkeypatch):
    verifier = AXEVerifier()

    fake_window = SimpleNamespace(
        descendants=lambda **kwargs: [
            SimpleNamespace(window_text=lambda: "hello world")
        ]
    )

    monkeypatch.setattr(
        "app.core.verifier._get_application_windows",
        lambda app: [fake_window],
    )

    result = verifier.verify_action(
        Action(
            tool="type_text",
            arguments={"text": "hello"},
        ),
        {"success": True, "application": "notepad"},
    )

    assert result["verified"] is True
    assert result["method"] == "notepad_editor_text"


def test_browser_type_text_verification_succeeds(monkeypatch):
    verifier = AXEVerifier()
    fake_page = FakePage(
        url="https://www.youtube.com/",
        title="YouTube",
        values=["", "Telugu movies"],
    )
    monkeypatch.setattr(browser_module, "_page", fake_page)
    monkeypatch.setattr(browser_module, "_browser", object())

    result = verifier.verify_action(
        Action(
            tool="type_text",
            arguments={"text": "Telugu movies"},
        ),
        {
            "success": True,
            "browser_open": True,
            "browser_url": "https://www.youtube.com/",
            "pre_action_state": {
                "browser_url": "https://www.youtube.com/",
                "editable_value_before": "",
            },
        },
    )

    assert result["verified"] is True
    assert result["method"] == "browser_editable_text"


def test_browser_focus_skips_hidden_and_disabled_inputs(monkeypatch):
    hidden = FakeEditable(None, visible=False)
    disabled = FakeEditable(None, enabled=False)
    visible = FakeEditable(None)
    page = FakeFocusPage([hidden, disabled, visible])

    hidden.page = page
    disabled.page = page
    visible.page = page

    monkeypatch.setattr(browser_module, "_page", page)

    result = browser_module.focus_editable()

    assert result["success"] is True
    assert result["focused"] is True
    assert page.focused is visible


def test_browser_focus_fails_without_editable_element(monkeypatch):
    page = FakeFocusPage([
        FakeEditable(None, visible=False),
        FakeEditable(None, enabled=False),
    ])
    for element in page.elements:
        element.page = page

    monkeypatch.setattr(browser_module, "_page", page)

    result = browser_module.focus_editable()

    assert result["success"] is False
    assert result["focused"] is False


def test_browser_type_text_focuses_before_typing_and_verifies(monkeypatch):
    from app.core.runtime import AXERuntime

    fake_page = FakePage(
        url="https://example.com",
        title="Example",
        values=[""],
    )
    monkeypatch.setattr(browser_module, "_page", fake_page)
    monkeypatch.setattr(browser_module, "_browser", object())
    monkeypatch.setattr(
        browser_module,
        "focus_editable",
        lambda: {"success": True, "focused": True},
    )

    def fake_write(text, interval=0.03):
        fake_page._values[:] = [text]

    monkeypatch.setattr(desktop.pyautogui, "write", fake_write)

    runtime = AXERuntime()
    runtime.browser_open = True

    result = runtime.execute_action(
        Action(
            tool="type_text",
            arguments={"text": "Telugu movies"},
        )
    )

    assert result["success"] is True
    assert result["verified"] is True


def test_browser_type_text_fails_closed_without_focus(monkeypatch):
    from app.core.runtime import AXERuntime

    fake_page = FakePage(
        url="https://example.com",
        title="Example",
        values=[""],
    )
    monkeypatch.setattr(browser_module, "_page", fake_page)
    monkeypatch.setattr(browser_module, "_browser", object())
    monkeypatch.setattr(
        browser_module,
        "focus_editable",
        lambda: {
            "success": False,
            "focused": False,
            "message": "No editable element.",
        },
    )

    def fail_if_typed(text, interval=0.03):
        raise AssertionError("PyAutoGUI must not run without focus")

    monkeypatch.setattr(desktop.pyautogui, "write", fail_if_typed)

    runtime = AXERuntime()
    runtime.browser_open = True

    result = runtime.execute_action(
        Action(
            tool="type_text",
            arguments={"text": "Telugu movies"},
        )
    )

    assert result["success"] is False
    assert result["verified"] is False
    assert result["result"]["message"] == "No editable element."


def test_browser_type_text_verification_fails_when_text_not_detected(monkeypatch):
    verifier = AXEVerifier()
    fake_page = FakePage(
        url="https://www.youtube.com/",
        title="YouTube",
        values=["some other value"],
    )
    monkeypatch.setattr(browser_module, "_page", fake_page)
    monkeypatch.setattr(browser_module, "_browser", object())

    result = verifier.verify_action(
        Action(
            tool="type_text",
            arguments={"text": "Telugu movies"},
        ),
        {
            "success": True,
            "browser_open": True,
            "browser_url": "https://www.youtube.com/",
            "pre_action_state": {
                "browser_url": "https://www.youtube.com/",
                "editable_value_before": "some other value",
            },
        },
    )

    assert result["verified"] is False
    assert result["method"] in {
        "browser_text_missing",
        "browser_text_mismatch",
    }


def test_browser_enter_verification_succeeds_on_navigation():
    verifier = AXEVerifier()

    result = verifier.verify_action(
        Action(tool="press_key", arguments={"key": "enter"}),
        {
            "success": True,
            "browser_open": True,
            "pre_action_state": {
                "application": "browser",
                "browser_url": "https://example.com",
                "browser_title": "Example",
                "editable_values": ["query"],
            },
            "post_action_state": {
                "application": "browser",
                "browser_url": "https://example.com/search?q=query",
                "browser_title": "Search results",
                "editable_values": ["query"],
            },
        },
    )

    assert result["verified"] is True
    assert result["method"] == "browser_key_state_transition"
    assert result["evidence"]["url_changed"] is True


def test_browser_enter_verification_succeeds_on_title_transition():
    verifier = AXEVerifier()

    result = verifier.verify_action(
        Action(tool="press_key", arguments={"key": "enter"}),
        {
            "success": True,
            "browser_open": True,
            "pre_action_state": {
                "application": "browser",
                "browser_url": "https://example.com",
                "browser_title": "Example",
                "editable_values": ["query"],
            },
            "post_action_state": {
                "application": "browser",
                "browser_url": "https://example.com",
                "browser_title": "Search results",
                "editable_values": ["query"],
            },
        },
    )

    assert result["verified"] is True
    assert result["evidence"]["title_changed"] is True


def test_browser_enter_verification_fails_without_state_change():
    verifier = AXEVerifier()

    result = verifier.verify_action(
        Action(tool="press_key", arguments={"key": "enter"}),
        {
            "success": True,
            "browser_open": True,
            "pre_action_state": {
                "application": "browser",
                "browser_url": "https://example.com",
                "browser_title": "Example",
                "editable_values": ["query"],
            },
            "post_action_state": {
                "application": "browser",
                "browser_url": "https://example.com",
                "browser_title": "Example",
                "editable_values": ["query"],
            },
        },
    )

    assert result["verified"] is False
    assert result["method"] == "browser_key_state_unchanged"


def test_browser_enter_verification_without_browser_context_fails_closed():
    verifier = AXEVerifier()

    result = verifier.verify_action(
        Action(tool="press_key", arguments={"key": "enter"}),
        {"success": True},
    )

    assert result["verified"] is False
    assert result["method"] == "key_missing_application"


def test_browser_navigation_verification_still_succeeds(monkeypatch):
    verifier = AXEVerifier()
    fake_page = FakePage(url="https://example.com", title="Example Domain")
    monkeypatch.setattr(browser_module, "_page", fake_page)
    monkeypatch.setattr(browser_module, "_browser", object())

    result = verifier.verify_action(
        Action(
            tool="navigate_browser",
            arguments={"url": "example.com"},
        ),
        {
            "success": True,
            "url": "https://example.com",
        },
    )

    assert result["verified"] is True
    assert result["method"] == "browser_hostname_navigation"


def test_browser_open_close_verification_still_succeeds(monkeypatch):
    verifier = AXEVerifier()
    fake_page = FakePage(url="https://example.com", title="Example Domain")
    monkeypatch.setattr(browser_module, "_page", fake_page)
    monkeypatch.setattr(browser_module, "_browser", object())

    open_result = verifier.verify_action(
        Action(
            tool="open_browser",
            arguments={},
        ),
        {"success": True, "url": "https://example.com"},
    )
    assert open_result["verified"] is True

    monkeypatch.setattr(browser_module, "_page", None)
    monkeypatch.setattr(browser_module, "_browser", None)

    close_result = verifier.verify_action(
        Action(
            tool="close_browser",
            arguments={},
        ),
        {"success": True},
    )
    assert close_result["verified"] is True


def test_desktop_type_text_still_succeeds(monkeypatch):
    calls = {}

    def fake_write(text, interval=0.03):
        calls["text"] = text
        calls["interval"] = interval

    monkeypatch.setattr(desktop.pyautogui, "write", fake_write)

    result = desktop.type_text("hello")

    assert result["success"] is True
    assert result["text"] == "hello"
    assert calls["text"] == "hello"
