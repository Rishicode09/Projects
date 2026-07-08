import pytest

from ai_agent.memory import ConversationMemory
from ai_agent.retry import retry_call


class Boom(Exception):
    pass


def test_retry_succeeds_after_transient_failures():
    calls = []

    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise Boom("transient")
        return "ok"

    result = retry_call(
        flaky, is_retryable=lambda e: True, max_attempts=3, base_delay=0, sleep=lambda _: None
    )

    assert result == "ok"
    assert len(calls) == 3


def test_retry_gives_up_after_max_attempts():
    calls = []

    def always_fails():
        calls.append(1)
        raise Boom("still broken")

    with pytest.raises(Boom):
        retry_call(
            always_fails,
            is_retryable=lambda e: True,
            max_attempts=3,
            base_delay=0,
            sleep=lambda _: None,
        )
    assert len(calls) == 3


def test_retry_does_not_retry_non_retryable():
    calls = []

    def fails():
        calls.append(1)
        raise Boom("fatal")

    with pytest.raises(Boom):
        retry_call(fails, is_retryable=lambda e: False, max_attempts=5, sleep=lambda _: None)
    assert len(calls) == 1


def test_memory_round_trip():
    memory = ConversationMemory(max_turns=5)
    memory.add_user_message("hi")
    memory.add_assistant_content([{"type": "text", "text": "hello"}])

    messages = memory.messages()

    assert messages[0] == {"role": "user", "content": "hi"}
    assert messages[1]["role"] == "assistant"


def test_memory_trims_whole_turns_keeping_tool_results():
    memory = ConversationMemory(max_turns=2)
    for i in range(3):
        memory.add_user_message(f"question {i}")
        memory.add_assistant_content([{"type": "tool_use", "id": f"t{i}"}])
        memory.add_tool_results([{"type": "tool_result", "tool_use_id": f"t{i}", "content": "42"}])
        memory.add_assistant_content([{"type": "text", "text": f"answer {i}"}])

    messages = memory.messages()

    # Only the two newest turns remain, each intact (4 messages per turn).
    assert len(messages) == 8
    assert messages[0] == {"role": "user", "content": "question 1"}
    # First message is always a plain user message, never an orphaned tool_result.
    assert isinstance(messages[0]["content"], str)


def test_memory_clear():
    memory = ConversationMemory()
    memory.add_user_message("hi")
    memory.clear()
    assert len(memory) == 0
