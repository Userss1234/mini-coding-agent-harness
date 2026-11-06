from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import tempfile
import threading
from concurrent.futures import Future
from contextlib import AsyncExitStack, ExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.streamable_http import streamable_http_client
from mcp.types import CallToolResult, PaginatedRequestParams

from .tools import Tool, ToolRegistry, ToolResult


@dataclass(frozen=True)
class ServerConfig:
    name: str
    transport: str
    options: dict[str, Any]
    tools: dict[str, str]
    timeout: float


def load_client_config(path: Path) -> list[ServerConfig]:
    if path.stat().st_size > 65536:
        raise ValueError("MCP client config exceeds 64 KiB")
    spec = json.loads(path.read_text(encoding="utf-8"))
    if spec.get("version") != 1 or not isinstance(spec.get("servers"), list):
        raise ValueError("MCP client config requires version=1 and servers")
    if not 1 <= len(spec["servers"]) <= 8:
        raise ValueError("Configure between 1 and 8 MCP servers")
    names = set()
    result = []
    for entry in spec["servers"]:
        name = entry["name"]
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,15}", name) or name in names:
            raise ValueError("Invalid or duplicate MCP server name")
        names.add(name)
        transport = entry.get("transport", "stdio")
        timeout = entry.get("timeout", 15)
        if isinstance(timeout, bool) or not isinstance(timeout, (float, int)) or not 1 <= timeout <= 60:
            raise ValueError("MCP deadline must be between 1 and 60 seconds")
        policies = entry.get("tools")
        if not isinstance(policies, dict) or not policies:
            raise ValueError("MCP tools need an explicit local allowlist")
        for tool, risk in policies.items():
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", tool) or risk not in {"read", "write"}:
                raise ValueError("Invalid MCP tool name or local risk mapping")
        if transport == "stdio":
            if not isinstance(entry.get("command"), str) or not entry["command"].strip():
                raise ValueError("MCP stdio command is required")
            args = entry.get("args", [])
            if not isinstance(args, list) or any(not isinstance(arg, str) for arg in args):
                raise ValueError("MCP args must be a string list, not a shell command")
            env = entry.get("env", {})
            if not isinstance(env, dict) or any(not isinstance(v, str) for v in env.values()):
                raise ValueError("MCP env maps child names to host environment variable names")
            cwd = entry.get("cwd", ".")
            if not isinstance(cwd, str):
                raise ValueError("MCP cwd must be a path string")
            entry["cwd"] = str((path.resolve().parent / cwd).resolve())
        elif transport == "http":
            url = urlsplit(entry.get("url", ""))
            local = url.hostname in {"localhost", "127.0.0.1", "::1"}
            if (url.scheme not in {"http", "https"} or not url.hostname or url.username
                    or url.password or url.query or url.fragment):
                raise ValueError("MCP URL must have no credentials, query or fragment")
            if not local and (not entry.get("allow_remote") or url.scheme != "https"):
                raise ValueError("Remote MCP requires explicit allow_remote and HTTPS")
        else:
            raise ValueError("MCP transport must be stdio or http")
        result.append(ServerConfig(name, transport, dict(entry), dict(policies), float(timeout)))
    return result


class MCPConnection:
    """A single owner task enters, uses and exits SDK async contexts on its own thread."""

    def __init__(self, config: ServerConfig):
        self.config = config
        self.environment = {key: os.environ[value] for key, value in config.options.get("env", {}).items()}
        token_var = config.options.get("token_env")
        self.token = os.environ[token_var] if token_var else None
        self.fingerprint = hashlib.sha256(json.dumps({
            "config": config.options,
            "environment_digest": hashlib.sha256(json.dumps(self.environment, sort_keys=True).encode()).hexdigest(),
            "token_digest": hashlib.sha256((self.token or "").encode()).hexdigest(),
        }, sort_keys=True).encode()).hexdigest()
        self.ready = threading.Event()
        self.closed = threading.Event()
        self.failed = threading.Event()
        self.initialized = False
        self.error: BaseException | None = None
        self.loop: asyncio.AbstractEventLoop | None = None
        self.task: asyncio.Task | None = None
        self.queue: asyncio.Queue | None = None
        self.descriptors: list[Any] = []
        self.thread = threading.Thread(target=self._run, name=f"mcp-{config.name}", daemon=True)

    def __enter__(self):
        self.thread.start()
        if not self.ready.wait(self.config.timeout + 5) or self.error is not None:
            self.close()
            raise RuntimeError(f"MCP {self.config.name} connection initialization failed") from self.error
        return self

    def __exit__(self, *_args):
        self.close()

    def _run(self):
        try:
            asyncio.run(self._serve())
        except BaseException as exc:
            self.error = exc
        finally:
            self.ready.set()
            self.closed.set()

    async def _serve(self):
        self.loop = asyncio.get_running_loop()
        self.task = asyncio.current_task()
        self.queue = asyncio.Queue()
        options = self.config.options
        async with AsyncExitStack() as stack:
            if self.config.transport == "stdio":
                errlog = stack.enter_context(tempfile.TemporaryFile(mode="w+", encoding="utf-8"))
                streams = await stack.enter_async_context(stdio_client(StdioServerParameters(
                    command=options["command"], args=options.get("args", []),
                    cwd=options.get("cwd"), env=self.environment,
                ), errlog=errlog))
            else:
                from httpx2 import AsyncClient

                headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
                http = await stack.enter_async_context(AsyncClient(
                    headers=headers, timeout=self.config.timeout, follow_redirects=False))
                streams = await stack.enter_async_context(streamable_http_client(options["url"], http_client=http))
            session = await stack.enter_async_context(ClientSession(
                streams[0], streams[1], read_timeout_seconds=self.config.timeout))
            await session.initialize()
            cursor = None
            for _ in range(20):
                page = await session.list_tools(params=PaginatedRequestParams(cursor=cursor))
                self.descriptors.extend(page.tools)
                if len(self.descriptors) > 1000:
                    raise ValueError("MCP tool discovery limit exceeded")
                cursor = page.next_cursor
                if not cursor:
                    break
            else:
                raise ValueError("MCP discovery pagination limit exceeded")
            self.initialized = True
            self.ready.set()
            while True:
                request = await self.queue.get()
                if request is None:
                    break
                name, arguments, future = request
                try:
                    value = await asyncio.wait_for(session.call_tool(
                        name, arguments, read_timeout_seconds=self.config.timeout * 2), self.config.timeout)
                    future.set_result(value)
                except Exception as exc:
                    self.failed.set()
                    future.set_exception(exc)
                    # No retry/reconnect after an uncertain remote execution.
                    break

    def call(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        if self.closed.is_set() or self.failed.is_set() or self.loop is None or self.queue is None:
            return ToolResult(False, "MCP connection is closed; explicit reconnect required",
                              {"tool_error": {"code": "mcp_disconnected", "retryable": False}})
        future: Future = Future()
        self.loop.call_soon_threadsafe(self.queue.put_nowait, (name, arguments, future))
        try:
            result = future.result(timeout=self.config.timeout + 5)
        except Exception as exc:
            timed_out = isinstance(exc, TimeoutError) or "timeout" in type(exc).__name__.lower()
            code = "mcp_timeout" if timed_out else "mcp_transport_error"
            return ToolResult(False, f"MCP call failed ({code}); remote outcome may be unknown. No automatic retry.",
                              {"tool_error": {"code": code, "retryable": False},
                               "remote_outcome_unknown": True})
        content = []
        if not isinstance(result, CallToolResult):
            return ToolResult(False, "Unsupported MCP result requires explicit operator handling",
                              {"tool_error": {"code": "mcp_result_unsupported", "retryable": False}})
        for block in getattr(result, "content", []):
            if getattr(block, "type", None) == "text":
                content.append(block.text)
        structured = result.structured_content
        if structured is not None:
            content.append(json.dumps(structured, ensure_ascii=False))
        output = "\n".join(content)
        ok = not result.is_error
        metadata: dict[str, Any] = {"mcp_server": self.config.name, "remote_tool": name,
                                    "output_truncated": len(output) > 12000}
        if not ok:
            metadata["tool_error"] = {"code": "mcp_tool_error", "retryable": False}
        return ToolResult(ok, output[:12000] or "(no text MCP content)", metadata)

    def close(self):
        if self.loop is not None and self.queue is not None and not self.closed.is_set():
            if not self.ready.is_set() and self.task is not None:
                self.loop.call_soon_threadsafe(self.task.cancel)
            else:
                self.loop.call_soon_threadsafe(self.queue.put_nowait, None)
        self.thread.join(timeout=self.config.timeout + 10)
        if self.thread.is_alive():
            raise RuntimeError("MCP shutdown did not finish within its deadline")
        if self.initialized and self.error is not None and not self.failed.is_set():
            raise RuntimeError("MCP session teardown failed") from self.error


def _remote_handler(connection: MCPConnection, name: str):
    def invoke(**arguments):
        return connection.call(name, arguments)
    return invoke


class ExternalMCPTools:
    def __init__(self, registry: ToolRegistry, config_path: Path | None,
                 expected_policy: dict[str, Any] | None = None):
        self.registry = registry
        self.path = config_path
        self.stack = ExitStack()
        self.names: list[str] = []
        self.expected_policy = expected_policy

    def __enter__(self):
        if self.path is None:
            if self.expected_policy:
                raise ValueError("Resume requires the original external MCP configuration")
            return self
        if self.path.resolve().is_relative_to(self.registry.workspace):
            raise ValueError("MCP operator configuration must be outside the agent workspace")
        try:
            connections = [MCPConnection(config) for config in load_client_config(self.path)]
            proposed = {f"mcp__{connection.config.name}__{name}": {
                "server_fingerprint": connection.fingerprint, "risk": risk,
            } for connection in connections for name, risk in connection.config.tools.items()}
            if self.expected_policy is not None and proposed != self.expected_policy:
                raise ValueError("MCP connection policy changed; refusing to launch servers during resume")
            for connection in connections:
                config = connection.config
                connection = self.stack.enter_context(connection)
                available = {tool.name: tool for tool in connection.descriptors}
                if len(available) != len(connection.descriptors):
                    raise ValueError("MCP discovery returned duplicate tool names")
                if not set(config.tools).issubset(available):
                    raise ValueError("Configured MCP allowlist includes undiscovered tools")
                fingerprint = connection.fingerprint
                for name, risk in config.tools.items():
                    local_name = f"mcp__{config.name}__{name}"
                    remote = available[name]
                    self.registry.register(Tool(
                        local_name, f"External MCP {config.name}: {remote.description or name}",
                        remote.input_schema, _remote_handler(connection, name), risk=f"external_{risk}",
                    ))
                    self.names.append(local_name)
                    self.registry.external_tool_policy[local_name] = {
                        "server_fingerprint": fingerprint, "risk": risk,
                    }
                self.registry.trace.log("mcp_client_connected", server=config.name,
                                        transport=config.transport, tools=list(config.tools))
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *args):
        try:
            return self.stack.__exit__(*args)
        finally:
            for name in self.names:
                self.registry._tools.pop(name, None)
                self.registry.external_tool_policy.pop(name, None)
