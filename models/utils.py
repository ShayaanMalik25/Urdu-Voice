"""Utility functions for STT and LLM models."""
import time
import logging
from typing import Literal

from livekit.agents import llm
from openai.types.chat import ChatCompletionMessageParam

# Whisper model types
WhisperModels = Literal[
    "base",
    "small",
    "medium",
    "large-v2",
    "large-v3",
    "large-v3-turbo",
]

logger = logging.getLogger(__name__)


class find_time:
    """Context manager for timing code execution."""
    def __init__(self, label: str):
        self.label = label
        self.start_time = None

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        end_time = time.perf_counter()
        elapsed_ms = (end_time - self.start_time) * 1000
        logger.debug(f"{self.label} took {elapsed_ms:.4f} ms")


def to_chat_ctx(chat_ctx: llm.ChatContext, cache_key: any) -> list[ChatCompletionMessageParam]:
    """Convert LiveKit chat context to OpenAI-compatible messages.
    
    Simplified version for Ollama compatibility.
    """
    messages = []
    for item in chat_ctx.items:
        if item.type == "message":
            messages.append({
                "role": item.role,  # type: ignore
                "content": "\n".join(item.content) if isinstance(item.content, list) else str(item.content),
            })
        elif item.type == "function_call":
            # Convert function call to assistant message with tool_calls
            messages.append({
                "role": "assistant",
                "tool_calls": [{
                    "id": item.call_id,
                    "type": "function",
                    "function": {
                        "name": item.name,
                        "arguments": item.arguments,
                    },
                }],
            })
        elif item.type == "function_call_output":
            messages.append({
                "role": "tool",
                "tool_call_id": item.call_id,
                "content": item.output,
            })
    return messages


def to_fnc_ctx(fnc_ctx: list[llm.FunctionTool]) -> list:
    """Convert LiveKit function tools to OpenAI tool parameters."""
    return [llm.utils.build_strict_openai_schema(fnc) for fnc in fnc_ctx]
