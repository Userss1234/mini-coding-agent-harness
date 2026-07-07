from __future__ import annotations

from harness.model_clients import OpenAICompatibleClient, create_default_model_client


def test_openai_compatible_client_converts_tool_calls() -> None:
    captured_payloads = []

    def fake_transport(payload):
        captured_payloads.append(payload)
        return {
            "choices": [{
                "message": {
                    "tool_calls": [{
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "read_file",
                            "arguments": '{"path": "README.md"}',
                        },
                    }],
                },
            }],
            "usage": {"prompt_tokens": 11, "completion_tokens": 7},
        }

    client = OpenAICompatibleClient(
        api_key="test-key",
        base_url="https://api.example.test",
        transport=fake_transport,
    )
    response = client.messages.create(
        model="deepseek-chat",
        system="system prompt",
        messages=[{"role": "user", "content": "inspect"}],
        tools=[{
            "name": "read_file",
            "description": "Read a file.",
            "input_schema": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        }],
        max_tokens=100,
    )

    payload = captured_payloads[0]
    assert payload["tools"][0]["type"] == "function"
    assert payload["tools"][0]["function"]["name"] == "read_file"
    assert payload["messages"][0] == {"role": "system", "content": "system prompt"}
    assert response.stop_reason == "tool_use"
    assert response.content[0].type == "tool_use"
    assert response.content[0].name == "read_file"
    assert response.content[0].input == {"path": "README.md"}
    assert response.usage.input_tokens == 11
    assert response.usage.output_tokens == 7


def test_openai_compatible_client_converts_tool_results_back_to_messages() -> None:
    captured_payloads = []

    def fake_transport(payload):
        captured_payloads.append(payload)
        return {
            "choices": [{"message": {"content": "done"}}],
            "usage": {"prompt_tokens": 3, "completion_tokens": 1},
        }

    client = OpenAICompatibleClient(
        api_key="test-key",
        base_url="https://api.example.test",
        transport=fake_transport,
    )
    response = client.messages.create(
        model="deepseek-chat",
        system="system prompt",
        messages=[
            {
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": "call_1",
                    "content": "file contents",
                }],
            }
        ],
        tools=[],
        max_tokens=100,
    )

    assert captured_payloads[0]["messages"][1] == {
        "role": "tool",
        "tool_call_id": "call_1",
        "content": "file contents",
    }
    assert response.stop_reason == "end_turn"
    assert response.content[0].text == "done"


def test_create_default_model_client_prefers_deepseek(monkeypatch) -> None:
    monkeypatch.setenv("MODEL_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-reasoner")
    monkeypatch.delenv("MODEL_ID", raising=False)

    client, config = create_default_model_client()

    assert isinstance(client, OpenAICompatibleClient)
    assert config.provider == "deepseek"
    assert config.default_model == "deepseek-reasoner"


def test_create_default_model_client_uses_anthropic_when_configured(monkeypatch) -> None:
    class FakeAnthropic:
        def __init__(self, base_url=None):
            self.base_url = base_url

    monkeypatch.delenv("MODEL_PROVIDER", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://anthropic.example.test")
    monkeypatch.setenv("MODEL_ID", "claude-test")

    client, config = create_default_model_client(FakeAnthropic)

    assert isinstance(client, FakeAnthropic)
    assert client.base_url == "https://anthropic.example.test"
    assert config.provider == "anthropic"
    assert config.default_model == "claude-test"
