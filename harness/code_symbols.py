from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any

from .retrieval import build_workspace_index


def _callee(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _callee(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _body_calls(node: ast.AST) -> set[str]:
    calls: set[str] = set()
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
        return calls
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            continue
        if isinstance(child, ast.Call):
            value = _callee(child.func)
            if value:
                calls.add(value)
        calls.update(_body_calls(child))
    return calls


class _Definitions(ast.NodeVisitor):
    def __init__(self) -> None:
        self.scope: list[str] = []
        self.items: list[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef, set[str]]] = []

    def _visit(self, node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef,
               callable_node: bool = False) -> None:
        name = ".".join([*self.scope, node.name])
        calls = set()
        if callable_node:
            for statement in node.body:
                if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call):
                    value = _callee(statement.value.func)
                    if value:
                        calls.add(value)
                calls.update(_body_calls(statement))
        self.items.append((name, node, calls))
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_FunctionDef(self, node):
        self._visit(node, True)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node):
        self._visit(node)


def search_code_symbols(workspace: Path, symbol: str, *, limit: int = 8) -> dict[str, Any]:
    if not symbol.strip() or not 1 <= limit <= 30:
        raise ValueError("A symbol and limit between 1 and 30 are required")
    root = workspace.resolve()
    index = build_workspace_index(root, glob_pattern="*.py", chunk_strategy="python")
    records = []
    skipped = 0
    for relative in sorted({chunk.path for chunk in index.chunks}):
        path = root / relative
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")[:200000]
            tree = ast.parse(text)
        except (OSError, SyntaxError, RecursionError):
            skipped += 1
            continue
        visitor = _Definitions()
        visitor.visit(tree)
        lines = text.splitlines()
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        for name, node, calls in visitor.items:
            start = min([node.lineno, *(item.lineno for item in getattr(node, "decorator_list", []))])
            end = getattr(node, "end_lineno", node.lineno)
            records.append({"symbol": name, "path": relative, "start_line": start,
                            "end_line": end, "indexed_source_sha256": digest,
                            "snippet": "\n".join(lines[start - 1:end])[:1000], "calls": sorted(calls)})
    target = symbol.strip()
    leaf = target.rsplit(".", 1)[-1]
    definitions = [item for item in records if item["symbol"] == target
                   or item["symbol"].endswith("." + target)]
    callers = [item for item in records if any(call == target or call.rsplit(".", 1)[-1] == leaf
                                              for call in item["calls"])]
    called = {name.rsplit(".", 1)[-1] for item in definitions for name in item["calls"]}
    callees = [item for item in records if item["symbol"].rsplit(".", 1)[-1] in called]
    result: dict[str, Any] = {
        "symbol": target, "definitions": [], "possible_callers": [], "possible_callees": [],
        "files_skipped_parse": skipped, "evidence_truncated": False,
        "analysis": "Python syntax-only candidate relationships; suffix matching can be ambiguous. Not runtime call resolution.",
        "index": index.metadata(),
    }
    for key, candidates in (("definitions", definitions), ("possible_callers", callers),
                            ("possible_callees", callees)):
        result["evidence_truncated"] |= len(candidates) > limit
        for item in candidates[:limit]:
            visible = {**item, "calls": item["calls"][:30], "calls_truncated": len(item["calls"]) > 30}
            result[key].append(visible)
            if len(json.dumps(result, ensure_ascii=False)) > 12000:
                result[key].pop()
                result["evidence_truncated"] = True
                break
    return result
