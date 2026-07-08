# AI Agent

A small, production-quality AI agent that **reasons, plans, and executes tasks** using Claude
and a modular tool system. Priorities, in order: reliability, simplicity, readability, performance.

## Architecture

```
ai_agent/
├── config.py          # Settings from environment / .env (no hidden globals)
├── logging_setup.py   # Structured JSON logging (or plain text)
├── retry.py           # Exponential backoff + jitter for transient failures
├── memory.py          # Conversation memory with turn-aware trimming
├── llm.py             # Anthropic Messages API wrapper (adaptive thinking, retries)
├── agent.py           # The loop: reason → call tools → feed results back → answer
├── cli.py             # One-shot mode and interactive REPL
└── tools/
    ├── base.py        # Tool ABC + ToolError
    ├── registry.py    # Registration, schemas, safe execution
    └── builtin/       # calculator, current_time, read_file, list_files
```

How a turn works:

1. The user message is appended to memory.
2. The model (default `claude-opus-4-8`, adaptive thinking on) receives the full history plus
   the tool schemas and decides whether to answer or call tools.
3. Tool calls are executed by the registry; failures come back as `is_error` tool results
   so the model can recover instead of the process crashing.
4. Results are fed back and the loop repeats, bounded by `AGENT_MAX_ITERATIONS`.
5. `pause_turn` is resumed automatically; `refusal` and `max_tokens` are reported clearly.

Transient API failures (network errors, 429s, 5xx) are retried with exponential backoff on
top of the SDK's built-in retries. Old turns are trimmed whole, so a `tool_use` block is
never separated from its `tool_result`.

## Setup

```bash
cd ai_agent
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # then set ANTHROPIC_API_KEY
```

## Usage

```bash
ai-agent "What is 12.5% compound interest on 3400 over 5 years?"   # one-shot
ai-agent                                                           # interactive REPL
python -m ai_agent "..."                                           # equivalent
```

REPL commands: `/tools` lists tools, `/clear` resets the conversation, `/exit` quits.

## Configuration

All settings come from the environment; a `.env` file in the working directory is read at
startup (existing environment variables win). See [.env.example](.env.example) for the full
list: model, token/iteration limits, memory size, retry policy, and log level/format.

## Adding a tool

Subclass `Tool`, then register it:

```python
from ai_agent.tools import Tool, ToolError

class WordCountTool(Tool):
    name = "word_count"
    description = "Count the words in a piece of text."
    input_schema = {
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
    }

    def run(self, tool_input):
        return str(len(tool_input["text"].split()))

registry.register(WordCountTool())
```

Raise `ToolError("message")` for expected failures — the message is returned to the model as
an error result. Unexpected exceptions are caught, logged, and reported generically.

## Development

```bash
python3 -m pytest      # test suite runs offline (fake LLM, no API key needed)
python3 -m ruff check .
```
