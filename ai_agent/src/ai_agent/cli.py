"""Command-line entry point: one-shot prompts or an interactive REPL."""

from __future__ import annotations

import argparse
import sys

from .agent import Agent
from .config import Config
from .llm import LLMClient
from .logging_setup import setup_logging
from .tools import default_registry


def build_agent(config: Config) -> Agent:
    logger = setup_logging(config.log_level, config.log_format)
    return Agent(
        config=config,
        llm=LLMClient(config, logger=logger.getChild("llm")),
        tools=default_registry(logger=logger.getChild("tools")),
        logger=logger.getChild("agent"),
    )


def repl(agent: Agent) -> None:
    print("AI agent ready. Type a task, or /tools, /clear, /exit.")
    while True:
        try:
            user_input = input("\nyou> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not user_input:
            continue
        if user_input in {"/exit", "/quit"}:
            return
        if user_input == "/clear":
            agent.memory.clear()
            print("(conversation cleared)")
            continue
        if user_input == "/tools":
            print("\n".join(agent_tool_summary(agent)))
            continue
        try:
            print(f"\nagent> {agent.run(user_input)}")
        except Exception as exc:  # keep the REPL alive on API failures
            print(f"\n[error] {exc}", file=sys.stderr)


def agent_tool_summary(agent: Agent) -> list[str]:
    return [
        f"- {schema['name']}: {schema['description'].split('.')[0]}."
        for schema in agent._tools.schemas()  # noqa: SLF001 - CLI is a friend of Agent
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ai-agent",
        description="An AI agent that reasons, plans, and executes tasks with Claude.",
    )
    parser.add_argument(
        "prompt",
        nargs="*",
        help="Task to run once. Omit to start an interactive session.",
    )
    parser.add_argument("--env-file", default=".env", help="Path to a .env file (default: .env)")
    args = parser.parse_args(argv)

    config = Config.from_env(args.env_file)
    agent = build_agent(config)

    if args.prompt:
        try:
            print(agent.run(" ".join(args.prompt)))
        except Exception as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        return 0

    repl(agent)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
