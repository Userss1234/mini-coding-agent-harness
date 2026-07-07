from __future__ import annotations

from dataclasses import dataclass
import json
import os
from types import SimpleNamespace
from typing import Any, Callable
from urllib import request


@dataclass
class ModelClientConfig:
    provider: str
    default_model: str


class OpenAICompatibleClient:
    """Adapter that exposes an Anthropic-like messages.create API."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        *,
        timeout: int = 60,
        transport: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    ):
        self.messages = OpenAICompatibleMessages(api_key, base_url, timeout, transport)


class OpenAICompatibleMessages:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        timeout: int,
        transport: Callable[[dict[str, Any]], dict[str, Any]] | None,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.transport = transport or self._http_post

    def create(
        self,
        *,
        model: str,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        max_tokens: int,
    ) -> Any:
        payload = {
            "model": model,
            "messages": _convert_messages(system, messages),
            "tools": [_convert_tool_schema(tool) for tool in tools],
            "tool_choice": "auto",
            "max_tokens": max_tokens,
        }
        data = self.transport(payload)
        return _parse_openai_response(data)

    def _http_post(self, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            f"{self.base_url}/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with request.urlopen(req, timeout=self.timeout) as response:  # nosec B310
            return json.loads(response.read().decode("utf-8"))


def create_default_model_client(anthropic_cls: Any | None = None) -> tuple[Any, ModelClientConfig]:
    provider = os.getenv("MODEL_PROVIDER", "").strip().lower()
    if provider in {"deepseek", "openai-compatible", "openai"} or (
        not provider and os.getenv("DEEPSEEK_API_KEY")
    ):
        api_key = _required_env("DEEPSEEK_API_KEY")
        base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        model = os.getenv("DEEPSEEK_MODEL") or os.getenv("MODEL_ID") or "deepseek-chat"
        return (
            OpenAICompatibleClient(api_key=api_key, base_url=base_url),
            ModelClientConfig(provider="deepseek", default_model=model),
        )

    if anthropic_cls is None:
        raise RuntimeError("anthropic package is not installed.")
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY is not set.")
    if os.getenv("ANTHROPIC_BASE_URL"):
        os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)
    model = os.getenv("MODEL_ID", "claude-3-5-sonnet-latest")
    return (
        anthropic_cls(base_url=os.getenv("ANTHROPIC_BASE_URL")),
        ModelClientConfig(provider="anthropic", default_model=model),
    )


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is not set.")
    return value


def _convert_tool_schema(tool: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool.get("description", ""),
            "parameters": tool.get("input_schema", {"type": "object", "properties": {}}),
        },
    }


def _convert_messages(system: str, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    converted: list[dict[str, Any]] = [{"role": "system", "content": system}]
    for item in messages:
        role = item.get("role")
        content = item.get("content")
        if role == "assistant" and isinstance(content, list):
            converted.append(_convert_assistant_blocks(content))
            continue
        if role == "user" and isinstance(content, list):
            converted.extend(_convert_tool_result_blocks(content))
            continue
        converted.append({"role": role, "content": str(content)})
    return converted


def _convert_assistant_blocks(blocks: list[Any]) -> dict[str, Any]:
    text_parts: list[str] = []
    tool_calls: list[dict[str, Any]] = []
    for block in blocks:
        block_type = getattr(block, "type", None)
        if block_type == "text":
            text_parts.append(str(getattr(block, "text", "")))
        elif block_type == "tool_use":
            tool_calls.append({
                "id": getattr(block, "id", ""),
                "type": "function",
                "function": {
                    "name": getattr(block, "name", ""),
                    "arguments": json.dumps(getattr(block, "input", {}) or {}),
                },
            })
    message: dict[str, Any] = {
        "role": "assistant",
        "content": "\n".join(part for part in text_parts if part).strip() or None,
    }
    if tool_calls:
        message["tool_calls"] = tool_calls
    return message


def _convert_tool_result_blocks(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    converted: list[dict[str, Any]] = []
    for block in blocks:
        if block.get("type") != "tool_result":
            continue
        converted.append({
            "role": "tool",
            "tool_call_id": block.get("tool_use_id", ""),
            "content": str(block.get("content", "")),
        })
    return converted


def _parse_openai_response(data: dict[str, Any]) -> Any:
    choice = (data.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    content_blocks = []
    text = message.get("content")
    if text:
        content_blocks.append(SimpleNamespace(type="text", text=text))
    for tool_call in message.get("tool_calls") or []:
        function = tool_call.get("function") or {}
        raw_arguments = function.get("arguments") or "{}"
        try:
            arguments = json.loads(raw_arguments)
        except json.JSONDecodeError:
            arguments = {}
        content_blocks.append(SimpleNamespace(
            type="tool_use",
            id=tool_call.get("id", ""),
            name=function.get("name", ""),
            input=arguments,
        ))
    usage = data.get("usage") or {}
    return SimpleNamespace(
        stop_reason="tool_use" if message.get("tool_calls") else "end_turn",
        content=content_blocks,
        usage=SimpleNamespace(
            input_tokens=int(usage.get("prompt_tokens", 0) or 0),
            output_tokens=int(usage.get("completion_tokens", 0) or 0),
        ),
    )
