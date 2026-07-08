from types import SimpleNamespace

import anthropic
import httpx

from ai_agent.agent import Agent
from ai_agent.config import Config
from ai_agent.llm import is_retryable_api_error
from ai_agent.tools import default_registry


def text_block(text):
    return SimpleNamespace(type="text", text=text)


def tool_use_block(block_id, name, tool_input):
    return SimpleNamespace(type="tool_use", id=block_id, name=name, input=tool_input)


def response(stop_reason, content):
    return SimpleNamespace(
        stop_reason=stop_reason,
        content=content,
        usage=SimpleNamespace(input_tokens=10, output_tokens=5),
    )


class FakeLLM:
    """Replays scripted responses and records what it was asked."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def complete(self, messages, tools, system):
        self.calls.append({"messages": messages, "tools": tools, "system": system})
        return self._responses.pop(0)


def make_agent(responses, max_iterations=10):
    config = Config(max_iterations=max_iterations)
    llm = FakeLLM(responses)
    return Agent(config, llm, default_registry()), llm


def test_plain_answer():
    agent, llm = make_agent([response("end_turn", [text_block("Paris")])])

    assert agent.run("Capital of France?") == "Paris"
    assert len(llm.calls) == 1
    # Tools were offered to the model.
    assert any(t["name"] == "calculator" for t in llm.calls[0]["tools"])


def test_tool_loop_executes_and_feeds_back_results():
    agent, llm = make_agent(
        [
            response(
                "tool_use",
                [
                    text_block("Let me compute that."),
                    tool_use_block("t1", "calculator", {"expression": "6 * 7"}),
                ],
            ),
            response("end_turn", [text_block("The answer is 42.")]),
        ]
    )

    assert agent.run("What is 6 * 7?") == "The answer is 42."
    assert len(llm.calls) == 2
    # The second request contains the tool result matched to the tool_use id.
    tool_result_msg = llm.calls[1]["messages"][-1]
    assert tool_result_msg["role"] == "user"
    [result] = tool_result_msg["content"]
    assert result["tool_use_id"] == "t1"
    assert result["content"] == "42"
    assert "is_error" not in result


def test_tool_failure_is_reported_not_raised():
    agent, llm = make_agent(
        [
            response("tool_use", [tool_use_block("t1", "calculator", {"expression": "1/0"})]),
            response("end_turn", [text_block("That division is undefined.")]),
        ]
    )

    assert agent.run("1/0?") == "That division is undefined."
    [result] = llm.calls[1]["messages"][-1]["content"]
    assert result["is_error"] is True


def test_parallel_tool_calls_return_all_results_in_one_message():
    agent, llm = make_agent(
        [
            response(
                "tool_use",
                [
                    tool_use_block("t1", "calculator", {"expression": "1 + 1"}),
                    tool_use_block("t2", "current_time", {}),
                ],
            ),
            response("end_turn", [text_block("done")]),
        ]
    )

    agent.run("both please")
    results = llm.calls[1]["messages"][-1]["content"]
    assert [r["tool_use_id"] for r in results] == ["t1", "t2"]


def test_pause_turn_resumes():
    agent, llm = make_agent(
        [
            response("pause_turn", [text_block("working...")]),
            response("end_turn", [text_block("finished")]),
        ]
    )

    assert agent.run("long task") == "finished"
    assert len(llm.calls) == 2


def test_refusal_returns_notice():
    agent, _ = make_agent([response("refusal", [])])
    assert "declined" in agent.run("bad request")


def test_iteration_limit_is_enforced():
    endless = [
        response("tool_use", [tool_use_block(f"t{i}", "current_time", {})]) for i in range(5)
    ]
    agent, llm = make_agent(endless, max_iterations=3)

    result = agent.run("loop forever")

    assert "Stopped after 3 steps" in result
    assert len(llm.calls) == 3


def test_memory_persists_across_turns():
    agent, llm = make_agent(
        [
            response("end_turn", [text_block("Hi Alice")]),
            response("end_turn", [text_block("Your name is Alice")]),
        ]
    )

    agent.run("I'm Alice")
    agent.run("What's my name?")

    second_call_messages = llm.calls[1]["messages"]
    assert second_call_messages[0] == {"role": "user", "content": "I'm Alice"}


def test_retryable_error_classification():
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")

    connection_error = anthropic.APIConnectionError(request=request)
    rate_limited = anthropic.RateLimitError(
        "slow down", response=httpx.Response(429, request=request), body=None
    )
    server_error = anthropic.InternalServerError(
        "oops", response=httpx.Response(500, request=request), body=None
    )
    bad_request = anthropic.BadRequestError(
        "bad", response=httpx.Response(400, request=request), body=None
    )

    assert is_retryable_api_error(connection_error)
    assert is_retryable_api_error(rate_limited)
    assert is_retryable_api_error(server_error)
    assert not is_retryable_api_error(bad_request)
    assert not is_retryable_api_error(ValueError("unrelated"))
