import pytest

from ai_agent.tools import (
    CalculatorTool,
    ClockTool,
    ListFilesTool,
    ReadFileTool,
    Tool,
    ToolError,
    ToolRegistry,
    default_registry,
)


class TestCalculator:
    def setup_method(self):
        self.calc = CalculatorTool()

    @pytest.mark.parametrize(
        ("expression", "expected"),
        [
            ("2 + 3 * 4", "14"),
            ("(2 + 3) ** 2", "25"),
            ("-7 // 2", "-4"),
            ("sqrt(16)", "4.0"),
            ("round(pi, 2)", "3.14"),
        ],
    )
    def test_evaluates(self, expression, expected):
        assert self.calc.run({"expression": expression}) == expected

    @pytest.mark.parametrize(
        "expression",
        [
            "__import__('os').system('id')",
            "().__class__",
            "open('/etc/passwd')",
            "x = 1",
            "'a' * 10",
            "2 ** 999999",
            "1 / 0",
            "",
        ],
    )
    def test_rejects_unsafe_or_invalid(self, expression):
        with pytest.raises(ToolError):
            self.calc.run({"expression": expression})


class TestClock:
    def test_returns_utc_by_default(self):
        result = ClockTool().run({})
        assert "UTC" in result

    def test_named_timezone(self):
        result = ClockTool().run({"timezone": "Europe/London"})
        assert "Europe/London" in result

    def test_unknown_timezone(self):
        with pytest.raises(ToolError, match="Unknown timezone"):
            ClockTool().run({"timezone": "Mars/Olympus_Mons"})


class TestFileTools:
    def test_read_file(self, tmp_path):
        (tmp_path / "note.txt").write_text("hello")
        assert ReadFileTool(tmp_path).run({"path": "note.txt"}) == "hello"

    def test_read_rejects_escape(self, tmp_path):
        with pytest.raises(ToolError, match="outside the workspace"):
            ReadFileTool(tmp_path).run({"path": "../../etc/passwd"})

    def test_read_missing_file(self, tmp_path):
        with pytest.raises(ToolError, match="No such file"):
            ReadFileTool(tmp_path).run({"path": "ghost.txt"})

    def test_list_files(self, tmp_path):
        (tmp_path / "sub").mkdir()
        (tmp_path / "a.txt").write_text("x")
        listing = ListFilesTool(tmp_path).run({})
        assert listing.splitlines() == ["sub/", "a.txt"]


class FailingTool(Tool):
    name = "failing"
    description = "always crashes"
    input_schema = {"type": "object", "properties": {}}

    def run(self, tool_input):
        raise RuntimeError("kaboom")


class TestRegistry:
    def test_execute_success(self):
        registry = default_registry()
        result = registry.execute("calculator", {"expression": "1 + 1"})
        assert not result.is_error
        assert result.content == "2"

    def test_unknown_tool_is_error_result(self):
        result = ToolRegistry().execute("nope", {})
        assert result.is_error
        assert "Unknown tool" in result.content

    def test_tool_error_becomes_error_result(self):
        registry = default_registry()
        result = registry.execute("calculator", {"expression": "1 / 0"})
        assert result.is_error
        assert "Division by zero" in result.content

    def test_unexpected_crash_is_contained(self):
        registry = ToolRegistry()
        registry.register(FailingTool())
        result = registry.execute("failing", {})
        assert result.is_error
        assert "kaboom" not in result.content  # internals are not leaked to the model

    def test_duplicate_registration_rejected(self):
        registry = ToolRegistry()
        registry.register(FailingTool())
        with pytest.raises(ValueError, match="already registered"):
            registry.register(FailingTool())

    def test_schemas_are_sorted_and_complete(self):
        schemas = default_registry().schemas()
        names = [schema["name"] for schema in schemas]
        assert names == sorted(names)
        assert all({"name", "description", "input_schema"} <= set(s) for s in schemas)
