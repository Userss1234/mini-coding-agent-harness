from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path
from typing import Any


def build_trace_report(trace_path: Path, output_path: Path) -> str:
    events, parse_errors = load_trace_events(trace_path)
    html = render_trace_html(trace_path, events, parse_errors)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    return html


def load_trace_events(trace_path: Path) -> tuple[list[dict[str, Any]], int]:
    events: list[dict[str, Any]] = []
    parse_errors = 0
    if not trace_path.exists():
        raise FileNotFoundError(f"Trace file not found: {trace_path}")

    for line in trace_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            parse_errors += 1
            continue
        if isinstance(item, dict):
            events.append(item)
        else:
            parse_errors += 1
    return events, parse_errors


def render_trace_html(
    trace_path: Path,
    events: list[dict[str, Any]],
    parse_errors: int,
) -> str:
    event_counts = Counter(str(item.get("event", "unknown")) for item in events)
    tool_events = [item for item in events if item.get("event") == "tool_call"]
    permission_audit = summarize_permission_events(tool_events)
    trace_summary = summarize_trace_events(events)
    failed_tools = [
        item
        for item in tool_events
        if not item.get("data", {}).get("ok", True)
    ]
    rows = "\n".join(_event_row(index, item) for index, item in enumerate(events, start=1))
    if not rows:
        rows = '<tr><td colspan="6">No events found.</td></tr>'
    generated = datetime.now().isoformat(timespec="seconds")
    event_breakdown = ", ".join(
        f"{escape(name)}: {count}"
        for name, count in sorted(event_counts.items())
    ) or "none"
    permission_breakdown = _format_counter_inline(permission_audit["decisions"])
    risk_breakdown = _format_counter_inline(permission_audit["risks"])
    tool_breakdown = _format_counter_inline(trace_summary["tools"])
    blocked_rows = _blocked_permission_rows(permission_audit["blocked_calls"])
    event_options = _select_options(event_counts)
    tool_options = _select_options(trace_summary["tools"])
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Mini Coding Agent Trace</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; color: #1f2937; }}
    h1 {{ margin-bottom: 4px; }}
    .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin: 18px 0; }}
    .metric {{ border: 1px solid #d1d5db; border-radius: 6px; padding: 10px; background: #f9fafb; }}
    .metric strong {{ display: block; font-size: 20px; }}
    .filters {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px; margin: 16px 0; }}
    .filters label {{ display: grid; gap: 5px; font-size: 13px; font-weight: bold; }}
    .filters input, .filters select {{ min-height: 36px; border: 1px solid #9ca3af; border-radius: 4px; padding: 6px 8px; background: white; }}
    .filter-result {{ margin: 8px 0; color: #4b5563; }}
    .table-wrap {{ max-height: 70vh; overflow: auto; border: 1px solid #d1d5db; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ border: 1px solid #d1d5db; padding: 8px; vertical-align: top; }}
    th {{ background: #f3f4f6; text-align: left; }}
    #events-table th {{ position: sticky; top: 0; z-index: 1; }}
    code, pre {{ font-family: Consolas, monospace; }}
    pre {{ white-space: pre-wrap; margin: 0; max-height: 240px; overflow: auto; }}
    .ok {{ color: #166534; font-weight: bold; }}
    .fail {{ color: #991b1b; font-weight: bold; }}
  </style>
</head>
<body>
  <h1>Mini Coding Agent Trace</h1>
  <p>Generated: {escape(generated)}</p>
  <p>Trace: <code>{escape(str(trace_path))}</code></p>
  <section class="summary">
    <div class="metric"><span>Events</span><strong>{len(events)}</strong></div>
    <div class="metric"><span>Tool calls</span><strong>{len(tool_events)}</strong></div>
    <div class="metric"><span>Failed tools</span><strong>{len(failed_tools)}</strong></div>
    <div class="metric"><span>Parse errors</span><strong>{parse_errors}</strong></div>
    <div class="metric"><span>Allowed calls</span><strong>{permission_audit["allowed_count"]}</strong></div>
    <div class="metric"><span>Blocked calls</span><strong>{permission_audit["blocked_count"]}</strong></div>
    <div class="metric"><span>Failed after allow</span><strong>{permission_audit["failed_after_allow_count"]}</strong></div>
    <div class="metric"><span>Duration</span><strong>{trace_summary["duration_seconds"]:.2f}s</strong></div>
    <div class="metric"><span>Model turns</span><strong>{trace_summary["model_turns"]}</strong></div>
    <div class="metric"><span>Input tokens</span><strong>{trace_summary["input_tokens"]}</strong></div>
    <div class="metric"><span>Output tokens</span><strong>{trace_summary["output_tokens"]}</strong></div>
  </section>
  <p>Event breakdown: {event_breakdown}</p>
  <p>Tool-call mix: {tool_breakdown}</p>
  <p>Permission decisions: {permission_breakdown}</p>
  <p>Risk classes: {risk_breakdown}</p>
  <h2>Blocked Permission Calls</h2>
  <table>
    <thead>
      <tr>
        <th>Tool</th>
        <th>Risk</th>
        <th>Permission</th>
        <th>Output</th>
      </tr>
    </thead>
    <tbody>
{blocked_rows}
    </tbody>
  </table>
  <h2>Events</h2>
  <section class="filters" aria-label="Trace event filters">
    <label>Search
      <input id="trace-search" type="search" placeholder="Search event data">
    </label>
    <label>Event
      <select id="event-filter">
        <option value="">All events</option>
{event_options}
      </select>
    </label>
    <label>Tool
      <select id="tool-filter">
        <option value="">All tools</option>
{tool_options}
      </select>
    </label>
    <label>Status
      <select id="status-filter">
        <option value="">All statuses</option>
        <option value="ok">ok</option>
        <option value="failed">failed</option>
        <option value="none">not applicable</option>
      </select>
    </label>
  </section>
  <p id="filter-result" class="filter-result" aria-live="polite">{len(events)} of {len(events)} events shown</p>
  <div class="table-wrap">
    <table id="events-table">
      <thead>
        <tr>
          <th>#</th>
          <th>Timestamp</th>
          <th>Event</th>
          <th>Tool</th>
          <th>Status</th>
          <th>Data</th>
        </tr>
      </thead>
      <tbody>
{rows}
        <tr id="no-matching-events" hidden><td colspan="6">No events match the current filters.</td></tr>
      </tbody>
    </table>
  </div>
  <script>
    (() => {{
      const rows = Array.from(document.querySelectorAll("#events-table .event-row"));
      const search = document.querySelector("#trace-search");
      const eventFilter = document.querySelector("#event-filter");
      const toolFilter = document.querySelector("#tool-filter");
      const statusFilter = document.querySelector("#status-filter");
      const result = document.querySelector("#filter-result");
      const empty = document.querySelector("#no-matching-events");

      function applyFilters() {{
        const query = search.value.trim().toLowerCase();
        let visible = 0;
        rows.forEach((row) => {{
          const matches = (!query || row.dataset.search.includes(query))
            && (!eventFilter.value || row.dataset.event === eventFilter.value)
            && (!toolFilter.value || row.dataset.tool === toolFilter.value)
            && (!statusFilter.value || row.dataset.status === statusFilter.value);
          row.hidden = !matches;
          if (matches) visible += 1;
        }});
        empty.hidden = visible !== 0;
        result.textContent = visible + " of " + rows.length + " events shown";
      }}

      [search, eventFilter, toolFilter, statusFilter].forEach((control) => {{
        control.addEventListener("input", applyFilters);
        control.addEventListener("change", applyFilters);
      }});
    }})();
  </script>
</body>
</html>
"""


def summarize_trace_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    tool_counts: Counter[str] = Counter()
    model_turns = 0
    input_tokens = 0
    output_tokens = 0

    for event in events:
        data = event.get("data", {})
        if not isinstance(data, dict):
            continue
        if event.get("event") == "tool_call":
            tool_counts[str(data.get("tool", "unknown"))] += 1
        if event.get("event") != "agent_response":
            continue
        model_turns += 1
        usage = data.get("usage", {})
        if isinstance(usage, dict):
            input_tokens += _safe_int(usage.get("input_tokens"))
            output_tokens += _safe_int(usage.get("output_tokens"))

    return {
        "duration_seconds": _trace_duration_seconds(events),
        "model_turns": model_turns,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "tools": dict(tool_counts),
    }


def summarize_permission_events(tool_events: list[dict[str, Any]]) -> dict[str, Any]:
    decisions: Counter[str] = Counter()
    risks: Counter[str] = Counter()
    blocked_calls: list[dict[str, str]] = []
    allowed_count = 0
    blocked_count = 0
    failed_after_allow_count = 0

    for event in tool_events:
        data = event.get("data", {})
        if not isinstance(data, dict):
            continue
        permission = str(data.get("permission", "missing_permission"))
        risk = str(data.get("risk", "unknown"))
        ok = bool(data.get("ok", False))
        decisions[permission] += 1
        risks[risk] += 1
        if permission == "allow":
            allowed_count += 1
            if not ok:
                failed_after_allow_count += 1
            continue
        blocked_count += 1
        first_line = str(data.get("output", "")).splitlines()[0] if data.get("output") else ""
        blocked_calls.append({
            "tool": str(data.get("tool", "unknown")),
            "risk": risk,
            "permission": permission,
            "output": first_line,
        })

    return {
        "allowed_count": allowed_count,
        "blocked_count": blocked_count,
        "failed_after_allow_count": failed_after_allow_count,
        "decisions": dict(decisions),
        "risks": dict(risks),
        "blocked_calls": blocked_calls,
    }


def _event_row(index: int, event: dict[str, Any]) -> str:
    data = event.get("data", {})
    if not isinstance(data, dict):
        data = {"value": data}
    tool = data.get("tool", "")
    ok_value = data.get("ok")
    if ok_value is True:
        status = '<span class="ok">ok</span>'
        status_name = "ok"
    elif ok_value is False:
        status = '<span class="fail">failed</span>'
        status_name = "failed"
    else:
        status = ""
        status_name = "none"
    data_json = json.dumps(data, ensure_ascii=False, indent=2, default=str)
    event_name = str(event.get("event", "unknown"))
    tool_name = str(tool)
    search_text = " ".join([
        str(event.get("timestamp", "")),
        event_name,
        tool_name,
        data_json,
    ]).lower()
    return (
        '      <tr class="event-row"'
        f' data-event="{escape(event_name, quote=True)}"'
        f' data-tool="{escape(tool_name, quote=True)}"'
        f' data-status="{status_name}"'
        f' data-search="{escape(search_text, quote=True)}">'
        f"<td>{index}</td>"
        f"<td>{escape(str(event.get('timestamp', '')))}</td>"
        f"<td>{escape(event_name)}</td>"
        f"<td>{escape(tool_name)}</td>"
        f"<td>{status}</td>"
        f"<td><pre>{escape(data_json)}</pre></td>"
        "</tr>"
    )


def _format_counter_inline(items: dict[str, int]) -> str:
    if not items:
        return "none"
    return ", ".join(
        f"{escape(name)}: {count}"
        for name, count in sorted(items.items())
    )


def _select_options(items: dict[str, int] | Counter[str]) -> str:
    return "\n".join(
        f'        <option value="{escape(name, quote=True)}">{escape(name)} ({count})</option>'
        for name, count in sorted(items.items())
    )


def _trace_duration_seconds(events: list[dict[str, Any]]) -> float:
    timestamps: list[datetime] = []
    for event in events:
        raw = event.get("timestamp")
        if not isinstance(raw, str):
            continue
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            continue
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        timestamps.append(parsed)
    if len(timestamps) < 2:
        return 0.0
    return max((max(timestamps) - min(timestamps)).total_seconds(), 0.0)


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _blocked_permission_rows(blocked_calls: list[dict[str, str]]) -> str:
    if not blocked_calls:
        return '      <tr><td colspan="4">No blocked calls recorded.</td></tr>'
    return "\n".join(
        "      <tr>"
        f"<td>{escape(item['tool'])}</td>"
        f"<td>{escape(item['risk'])}</td>"
        f"<td>{escape(item['permission'])}</td>"
        f"<td>{escape(item['output'])}</td>"
        "</tr>"
        for item in blocked_calls
    )
