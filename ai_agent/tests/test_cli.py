from types import SimpleNamespace

import ai_agent.cli as cli
from ai_agent.agent import Agent
from ai_agent.config import Config
from ai_agent.tools import default_registry


class OneShotLLM:
    def complete(self, messages, tools, system):
        return SimpleNamespace(
            stop_reason="end_turn",
            content=[SimpleNamespace(type="text", text="42")],
            usage=SimpleNamespace(input_tokens=1, output_tokens=1),
        )


def test_main_one_shot_prints_answer(monkeypatch, capsys, tmp_path):
    def fake_build_agent(config):
        return Agent(config, OneShotLLM(), default_registry())

    monkeypatch.setattr(cli, "build_agent", fake_build_agent)

    exit_code = cli.main(["what is 6*7", "--env-file", str(tmp_path / "absent.env")])

    assert exit_code == 0
    assert capsys.readouterr().out.strip() == "42"


def test_main_reports_failures_with_nonzero_exit(monkeypatch, capsys, tmp_path):
    class BrokenAgent:
        def run(self, _):
            raise RuntimeError("api down")

    monkeypatch.setattr(cli, "build_agent", lambda config: BrokenAgent())

    exit_code = cli.main(["hello", "--env-file", str(tmp_path / "absent.env")])

    assert exit_code == 1
    assert "api down" in capsys.readouterr().err


def test_tool_summary_lists_builtin_tools():
    agent = Agent(Config(), OneShotLLM(), default_registry())
    summary = "\n".join(cli.agent_tool_summary(agent))
    for name in ("calculator", "current_time", "read_file", "list_files"):
        assert name in summary
