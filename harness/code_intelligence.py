from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
import queue
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from urllib.request import url2pathname

from .retrieval import build_workspace_index, tokenize_query


def repository_map(workspace: Path, query: str = "", max_chars: int = 6000) -> dict[str, Any]:
    if not 500 <= max_chars <= 12000:
        raise ValueError("Repository map budget must be 500..12000 characters")
    root = workspace.resolve()
    index = build_workspace_index(root, glob_pattern="*.py", chunk_strategy="python")
    records: list[dict[str, Any]] = []
    tokens = set(tokenize_query(query))
    skipped = 0
    for name in sorted({c.path for c in index.chunks}):
        path = root / name
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")[:200000]
            tree = ast.parse(text)
        except (OSError, SyntaxError, RecursionError):
            skipped += 1
            continue
        symbols = []
        imports = []
        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imports.append(ast.unparse(node)[:300])
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                symbols.append({"name": node.name, "kind": "function", "line": node.lineno,
                                "signature": (node.name + "(" + ast.unparse(node.args) + ")")[:400]})
            if isinstance(node, ast.ClassDef):
                symbols.append({"name": node.name, "kind": "class", "line": node.lineno,
                                "methods": [c.name for c in node.body if isinstance(
                                    c, (ast.FunctionDef, ast.AsyncFunctionDef))][:20]})
        relevance = len(tokens & set(tokenize_query(name + " " + json.dumps(symbols))))
        records.append({"path": name, "symbols": symbols[:30], "imports": imports[:20],
                        "indexed_source_sha256": hashlib.sha256(text.encode()).hexdigest(),
                        "query_overlap": relevance})
    records.sort(key=lambda item: (-item["query_overlap"], item["path"]))
    result: dict[str, Any] = {"files": [], "files_available": len(records), "parse_skipped": skipped,
                              "truncated": False, "budget_chars": max_chars,
                              "analysis": "Budgeted Python AST map; imports are syntax hints, not resolved dependencies"}
    for record in records:
        result["files"].append(record)
        if len(json.dumps(result, ensure_ascii=True)) > max_chars:
            result["files"].pop()
            result["truncated"] = True
            break
    return result


class PythonLSP:
    """One request-scoped trusted pylsp process using its own JSON-RPC stream library."""

    def __init__(self, root: Path, timeout: float = 10):
        if not 0 < timeout <= 30:
            raise ValueError("LSP timeout must be within (0,30] seconds")
        self.root, self.timeout = root.resolve(), timeout
        self.messages: queue.Queue = queue.Queue(maxsize=256)
        self.next_id = 0
        self.notifications: list[dict[str, Any]] = []

    def __enter__(self):
        if importlib.util.find_spec("pylsp") is None:
            raise RuntimeError('Python navigation requires the optional .[codeintel] dependencies')
        from pylsp_jsonrpc.streams import JsonRpcStreamReader, JsonRpcStreamWriter

        self.temp = tempfile.TemporaryDirectory(prefix="mini-agent-lsp-")
        allowed = {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "HOME", "USERPROFILE",
                   "APPDATA", "LOCALAPPDATA"}
        env = {key: value for key, value in os.environ.items() if key.upper() in allowed}
        for key in ("HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "XDG_CACHE_HOME"):
            env[key] = self.temp.name
        try:
            self.process = subprocess.Popen(
                [sys.executable, "-I", "-m", "pylsp"], cwd=self.temp.name, env=env,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            self.reader = JsonRpcStreamReader(self.process.stdout)
            self.writer = JsonRpcStreamWriter(self.process.stdin)

            def read():
                try:
                    self.reader.listen(self.messages.put_nowait)
                except Exception:
                    pass
                finally:
                    try:
                        self.messages.put_nowait({"closed": True})
                    except queue.Full:
                        pass

            self.thread = threading.Thread(target=read, name="python-lsp-reader", daemon=True)
            self.thread.start()
            self.settings = {"pylsp": {"configurationSources": [], "plugins": {
                "pycodestyle": {"enabled": False}, "mccabe": {"enabled": False},
                "pydocstyle": {"enabled": False}, "pylint": {"enabled": False},
                "flake8": {"enabled": False}, "autopep8": {"enabled": False},
                "yapf": {"enabled": False}, "jedi_completion": {"enabled": False},
                "pyflakes": {"enabled": True}, "jedi_definition": {"enabled": True},
                "jedi_references": {"enabled": True},
            }}}
            self.request("initialize", {"processId": os.getpid(), "rootUri": self.root.as_uri(),
                                       "capabilities": {"workspace": {"configuration": False}}})
            self.notify("initialized", {})
            self.notify("workspace/didChangeConfiguration", {"settings": self.settings})
            return self
        except BaseException:
            self.__exit__(*sys.exc_info())
            raise

    def notify(self, method: str, params: dict[str, Any]) -> None:
        self.writer.write({"jsonrpc": "2.0", "method": method, "params": params})

    def receive(self, deadline: float) -> dict[str, Any]:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Python language server deadline exceeded")
        try:
            message = self.messages.get(timeout=remaining)
        except queue.Empty:
            raise TimeoutError("Python language server deadline exceeded") from None
        if message.get("closed"):
            raise RuntimeError("Python language server disconnected")
        if "method" in message:
            if "id" in message:
                result: Any = None
                if message["method"] == "workspace/configuration":
                    result = [self.settings.get("pylsp", {}) for _ in message.get("params", {}).get("items", [])]
                self.writer.write({"jsonrpc": "2.0", "id": message["id"], "result": result})
            else:
                self.notifications.append(message)
        return message

    def request(self, method: str, params: dict[str, Any]) -> Any:
        self.next_id += 1
        ident = self.next_id
        self.writer.write({"jsonrpc": "2.0", "id": ident, "method": method, "params": params})
        deadline = time.monotonic() + self.timeout
        while True:
            message = self.receive(deadline)
            if message.get("id") == ident and "method" not in message:
                if "error" in message:
                    raise RuntimeError("Python language server rejected request")
                return message.get("result")

    def diagnostics(self, uri: str) -> list[dict[str, Any]]:
        deadline = time.monotonic() + self.timeout
        while True:
            for message in self.notifications:
                if (message.get("method") == "textDocument/publishDiagnostics"
                        and message.get("params", {}).get("uri") == uri):
                    return message["params"].get("diagnostics", [])
            self.receive(deadline)

    def __exit__(self, *args):
        process = getattr(self, "process", None)
        if process is not None:
            if process.poll() is None:
                try:
                    if not args or args[0] is None:
                        self.timeout = min(self.timeout, 2)
                        self.request("shutdown", {})
                    self.notify("exit", {})
                    process.wait(timeout=1)
                except (OSError, RuntimeError, TimeoutError, AttributeError, subprocess.TimeoutExpired):
                    process.kill()
                    process.wait(timeout=5)
            if hasattr(self, "thread"):
                self.thread.join(timeout=2)
            for stream in (process.stdin, process.stdout):
                if stream is not None:
                    stream.close()
            if hasattr(self, "thread") and self.thread.is_alive():
                raise RuntimeError("Language server reader did not stop")
        if hasattr(self, "temp"):
            self.temp.cleanup()


def navigate_python(workspace: Path, path: str, line: int, column: int = 1,
                    operation: str = "definition", timeout: float = 10) -> dict[str, Any]:
    if operation not in {"definition", "references", "diagnostics"}:
        raise ValueError("Unknown Python navigation operation")
    root = workspace.resolve()
    index = build_workspace_index(root, glob_pattern="*.py")
    hashes = {c.path: c.source_sha256 for c in index.chunks}
    if path not in hashes or line < 1 or column < 1:
        raise ValueError("Navigation requires a safe indexed Python file and positive position")
    target = root / path
    text = target.read_text(encoding="utf-8", errors="replace")[:200000]
    lines = text.splitlines()
    if line > len(lines) or column > len(lines[line - 1]) + 1:
        raise ValueError("Navigation position is outside the indexed source")
    position = {"line": line - 1, "character": len(lines[line - 1][:column - 1].encode("utf-16-le")) // 2}
    with PythonLSP(root, timeout) as server:
        uri = target.as_uri()
        server.notify("textDocument/didOpen", {"textDocument": {
            "uri": uri, "languageId": "python", "version": 1, "text": text}})
        if operation == "diagnostics":
            raw = [{"uri": uri, "range": d.get("range"), "diagnostic": d}
                   for d in server.diagnostics(uri)]
        else:
            params: dict[str, Any] = {"textDocument": {"uri": uri}, "position": position}
            if operation == "references":
                params["context"] = {"includeDeclaration": True}
            raw = server.request("textDocument/" + operation, params) or []
            if isinstance(raw, dict):
                raw = [raw]
    current = build_workspace_index(root, glob_pattern="*.py")
    current_hashes = {c.path: c.source_sha256 for c in current.chunks}
    if current_hashes.get(path) != hashes[path]:
        raise RuntimeError("Source changed during Python navigation; query again")
    matches = []
    for item in raw[:100]:
        parsed = urlsplit(item.get("uri", item.get("targetUri", "")))
        if parsed.scheme != "file" or parsed.netloc not in {"", "localhost"}:
            continue
        source = Path(url2pathname(parsed.path)).resolve()
        if not source.is_relative_to(root):
            continue
        relative = source.relative_to(root).as_posix()
        if relative not in hashes or current_hashes.get(relative) != hashes[relative]:
            continue
        region = item.get("range", item.get("targetSelectionRange")) or {}
        start = region.get("start", {})
        matches.append({"path": relative, "line": int(start.get("line", 0)) + 1,
                        "column_utf16": int(start.get("character", 0)) + 1,
                        "range": region, "indexed_source_sha256": hashes[relative],
                        **({"diagnostic": item["diagnostic"]} if "diagnostic" in item else {})})
    return {"operation": operation, "provider": "python-lsp-server / Jedi", "matches": matches[:30],
            "truncated": len(raw) > 30, "analysis": "Language-server static analysis; not runtime dispatch proof"}
