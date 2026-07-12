from __future__ import annotations

from dataclasses import dataclass
import fnmatch
import math
from pathlib import Path
from typing import Any


IGNORED_PATH_PARTS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    "artifacts",
    "eval_runs",
}

IGNORED_FILE_NAMES = {
    ".env",
    "trace.jsonl",
    "EVAL.json",
    "COMPARE.json",
}

TEXT_SUFFIXES = {
    ".css",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".jsx",
    ".md",
    ".py",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}


@dataclass(frozen=True)
class RetrievalChunk:
    path: str
    start_line: int
    end_line: int
    text: str
    tokens: tuple[str, ...]


@dataclass(frozen=True)
class RetrievalIndex:
    chunks: tuple[RetrievalChunk, ...]
    files_indexed: int
    files_skipped: int
    chunks_indexed: int
    ignored_parts: tuple[str, ...]
    ignored_names: tuple[str, ...]

    def metadata(self) -> dict[str, Any]:
        return {
            "files_indexed": self.files_indexed,
            "files_skipped": self.files_skipped,
            "chunks_indexed": self.chunks_indexed,
            "ignored_parts": list(self.ignored_parts),
            "ignored_names": list(self.ignored_names),
        }


def tokenize_query(text: str) -> list[str]:
    tokens: list[str] = []
    current: list[str] = []
    for char in text.lower():
        if char.isalnum():
            current.append(char)
        elif current:
            tokens.append("".join(current))
            current = []
    if current:
        tokens.append("".join(current))
    return [token for token in tokens if len(token) >= 2]


def build_workspace_index(
    workspace: Path,
    *,
    glob_pattern: str = "*",
    chunk_lines: int = 80,
    overlap: int = 10,
    max_file_chars: int = 200_000,
) -> RetrievalIndex:
    root = workspace.resolve()
    chunk_size = max(int(chunk_lines), 1)
    overlap_size = max(min(int(overlap), chunk_size - 1), 0)
    chunks: list[RetrievalChunk] = []
    files_indexed = 0
    files_skipped = 0

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        rel_text = _normalize_path(rel)
        if _path_is_ignored(rel) or not _matches_glob(rel_text, glob_pattern) or not _looks_textual(path):
            files_skipped += 1
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            files_skipped += 1
            continue
        if "\x00" in text:
            files_skipped += 1
            continue
        if len(text) > max_file_chars:
            text = text[:max_file_chars]
        file_chunks = _chunk_file(rel_text, text, chunk_size, overlap_size)
        if file_chunks:
            chunks.extend(file_chunks)
            files_indexed += 1
        else:
            files_skipped += 1

    return RetrievalIndex(
        chunks=tuple(chunks),
        files_indexed=files_indexed,
        files_skipped=files_skipped,
        chunks_indexed=len(chunks),
        ignored_parts=tuple(sorted(IGNORED_PATH_PARTS)),
        ignored_names=tuple(sorted(IGNORED_FILE_NAMES)),
    )


def search_workspace(
    workspace: Path,
    query: str,
    *,
    glob_pattern: str = "*",
    limit: int = 5,
    chunk_lines: int = 80,
    overlap: int = 10,
    max_chars_per_chunk: int = 1200,
) -> dict[str, Any]:
    query_text = str(query).strip()
    tokens = tokenize_query(query_text)
    index = build_workspace_index(
        workspace,
        glob_pattern=glob_pattern,
        chunk_lines=chunk_lines,
        overlap=overlap,
    )
    if not tokens or limit <= 0:
        return {"query": query_text, "tokens": tokens, "matches": [], "index": index.metadata()}

    doc_freq: dict[str, int] = {}
    for chunk in index.chunks:
        chunk_terms = set(chunk.tokens)
        for token in tokens:
            if token in chunk_terms:
                doc_freq[token] = doc_freq.get(token, 0) + 1

    scored: list[dict[str, Any]] = []
    total_chunks = max(len(index.chunks), 1)
    for chunk in index.chunks:
        score, details = _score_chunk(chunk, tokens, query_text, doc_freq, total_chunks)
        if score <= 0:
            continue
        snippet = chunk.text
        if len(snippet) > max_chars_per_chunk:
            snippet = snippet[:max_chars_per_chunk] + f"\n... ({len(snippet) - max_chars_per_chunk} more chars)"
        scored.append({
            "path": chunk.path,
            "score": round(score, 3),
            "text_score": round(details["text_score"], 3),
            "path_score": round(details["path_score"], 3),
            "start_line": chunk.start_line,
            "end_line": chunk.end_line,
            "snippet": snippet,
        })

    scored.sort(key=lambda item: (-float(item["score"]), str(item["path"]), int(item["start_line"])))
    return {
        "query": query_text,
        "tokens": tokens,
        "matches": scored[:max(int(limit), 0)],
        "index": index.metadata(),
        "retrieval": "local_chunk_lexical_scoring",
    }


def explain_retrieval_plan(
    workspace: Path,
    query: str,
    *,
    glob_pattern: str = "*",
    limit: int = 5,
    chunk_lines: int = 80,
    overlap: int = 10,
    read_window: int = 20,
    max_chars_per_chunk: int = 1200,
) -> dict[str, Any]:
    result = search_workspace(
        workspace,
        query,
        glob_pattern=glob_pattern,
        limit=limit,
        chunk_lines=chunk_lines,
        overlap=overlap,
        max_chars_per_chunk=max_chars_per_chunk,
    )
    plan = build_read_plan(result.get("matches") or [], read_window=max(int(read_window), 0))
    result["read_plan"] = plan
    return result


def build_read_plan(matches: list[dict[str, Any]], *, read_window: int = 20) -> list[dict[str, Any]]:
    plan: list[dict[str, Any]] = []
    seen: set[tuple[str, int, int]] = set()
    for index, item in enumerate(matches, start=1):
        path = str(item.get("path", "")).strip()
        if not path:
            continue
        start_line = max(int(item.get("start_line", 1)) - read_window, 1)
        end_line = max(int(item.get("end_line", start_line)) + read_window, start_line)
        key = (path, start_line, end_line)
        if key in seen:
            continue
        seen.add(key)
        plan.append({
            "step": len(plan) + 1,
            "path": path,
            "start_line": start_line,
            "end_line": end_line,
            "score": item.get("score", 0),
            "reason": f"ranked match #{index} for the retrieval query",
            "read_file_args": {
                "path": path,
                "start_line": start_line,
                "end_line": end_line,
            },
        })
    return plan


def format_index_summary(index: RetrievalIndex) -> str:
    return (
        "# Workspace Retrieval Index\n\n"
        f"- Files indexed: {index.files_indexed}\n"
        f"- Files skipped: {index.files_skipped}\n"
        f"- Chunks indexed: {index.chunks_indexed}\n"
        f"- Retrieval: local chunk lexical scoring\n"
        f"- Ignored path parts: {', '.join(index.ignored_parts)}\n"
        f"- Ignored file names: {', '.join(index.ignored_names)}\n"
    )


def format_search_results(result: dict[str, Any]) -> str:
    matches = result.get("matches") or []
    query = result.get("query") or ""
    if not matches:
        return f"# RAG Search\n\n- Query: {query}\n- Matches: 0\n\n(no matching context)"

    sections = []
    for item in matches:
        sections.append(
            "## `{path}` (score {score}, lines {start_line}-{end_line})\n\n"
            "```text\n{snippet}\n```".format(
                path=item["path"],
                score=item["score"],
                start_line=item["start_line"],
                end_line=item["end_line"],
                snippet=item["snippet"],
            )
        )
    return "# RAG Search\n\n- Query: {query}\n- Matches: {count}\n- Retrieval: local chunk lexical scoring\n\n{sections}\n".format(
        query=query,
        count=len(matches),
        sections="\n\n".join(sections),
    )


def format_retrieval_explanation(result: dict[str, Any]) -> str:
    matches = result.get("matches") or []
    plan = result.get("read_plan") or []
    query = result.get("query") or ""
    if not matches:
        return f"# RAG Read Plan\n\n- Query: {query}\n- Matches: 0\n\n(no matching context)"

    plan_rows = []
    for item in plan:
        args = item.get("read_file_args") or {}
        plan_rows.append(
            "{step}. `read_file(path=\"{path}\", start_line={start}, end_line={end})` - score {score}; {reason}.".format(
                step=item.get("step"),
                path=args.get("path"),
                start=args.get("start_line"),
                end=args.get("end_line"),
                score=item.get("score"),
                reason=item.get("reason"),
            )
        )
    chunk_rows = []
    for item in matches:
        chunk_rows.append(
            "- `{path}` lines {start_line}-{end_line}, score {score}".format(
                path=item.get("path"),
                start_line=item.get("start_line"),
                end_line=item.get("end_line"),
                score=item.get("score"),
            )
        )
    return "# RAG Read Plan\n\n- Query: {query}\n- Matches: {count}\n- Retrieval: local chunk lexical scoring\n\n## Read Plan\n\n{plan}\n\n## Matched Chunks\n\n{chunks}\n".format(
        query=query,
        count=len(matches),
        plan="\n".join(plan_rows) or "(no read plan)",
        chunks="\n".join(chunk_rows),
    )


def format_retrieved_context(result: dict[str, Any]) -> str:
    reads = result.get("reads") or []
    query = result.get("query") or ""
    if not reads:
        return f"# Retrieved Context\n\n- Query: {query}\n- Reads: 0\n\n(no readable context)"

    sections = []
    for item in reads:
        args = item.get("read_file_args") or {}
        if item.get("ok"):
            sections.append(
                "## Step {step}: `{path}` lines {start}-{end}\n\n"
                "```text\n{text}\n```".format(
                    step=item.get("step"),
                    path=args.get("path"),
                    start=args.get("start_line"),
                    end=args.get("end_line"),
                    text=item.get("text", ""),
                )
            )
        else:
            sections.append(
                "## Step {step}: `{path}` lines {start}-{end}\n\n"
                "Read failed: {error}".format(
                    step=item.get("step"),
                    path=args.get("path"),
                    start=args.get("start_line"),
                    end=args.get("end_line"),
                    error=item.get("error", "unknown error"),
                )
            )
    return "# Retrieved Context\n\n- Query: {query}\n- Reads: {count}\n- Retrieval: local chunk lexical scoring\n\n{sections}\n".format(
        query=query,
        count=len(reads),
        sections="\n\n".join(sections),
    )


def _chunk_file(path: str, text: str, chunk_lines: int, overlap: int) -> list[RetrievalChunk]:
    lines = text.splitlines()
    if not lines:
        return []
    chunks: list[RetrievalChunk] = []
    step = max(chunk_lines - overlap, 1)
    start = 0
    while start < len(lines):
        end = min(start + chunk_lines, len(lines))
        snippet = "\n".join(lines[start:end])
        chunks.append(
            RetrievalChunk(
                path=path,
                start_line=start + 1,
                end_line=end,
                text=snippet,
                tokens=tuple(tokenize_query(path + "\n" + snippet)),
            )
        )
        if end == len(lines):
            break
        start += step
    return chunks


def _score_chunk(
    chunk: RetrievalChunk,
    tokens: list[str],
    query: str,
    doc_freq: dict[str, int],
    total_chunks: int,
) -> tuple[float, dict[str, float]]:
    path_text = chunk.path.lower().replace("_", " ").replace("-", " ").replace("/", " ")
    body_text = chunk.text.lower()
    text_score = 0.0
    path_score = 0.0
    for token in tokens:
        idf = math.log((total_chunks + 1) / (doc_freq.get(token, 0) + 1)) + 1.0
        body_count = min(body_text.count(token), 5)
        if body_count:
            text_score += body_count * idf
        if token in path_text:
            path_score += 3.0 * idf
    if query and query.lower() in body_text:
        text_score += 5.0
    if any(marker in body_text for marker in ("def ", "class ", "function ", "describe(", "it(")):
        text_score += 0.5
    return text_score + path_score, {"text_score": text_score, "path_score": path_score}


def _path_is_ignored(rel: Path) -> bool:
    if rel.name in IGNORED_FILE_NAMES:
        return True
    return any(part in IGNORED_PATH_PARTS or (part.startswith(".") and part != ".") for part in rel.parts)


def _matches_glob(path: str, glob_pattern: str) -> bool:
    patterns = [item.strip() for item in glob_pattern.split(",") if item.strip()] or ["*"]
    return any(fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(Path(path).name, pattern) for pattern in patterns)


def _looks_textual(path: Path) -> bool:
    if path.suffix.lower() in TEXT_SUFFIXES:
        return True
    return path.suffix == ""


def _normalize_path(path: Path) -> str:
    return str(path).replace("\\", "/")
