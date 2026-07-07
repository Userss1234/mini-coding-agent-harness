from __future__ import annotations

from collections import Counter
from datetime import datetime
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
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ border: 1px solid #d1d5db; padding: 8px; vertical-align: top; }}
    th {{ background: #f3f4f6; text-align: left; }}
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
  </section>
  <p>Event breakdown: {event_breakdown}</p>
  <table>
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
    </tbody>
  </table>
</body>
</html>
"""


def _event_row(index: int, event: dict[str, Any]) -> str:
    data = event.get("data", {})
    if not isinstance(data, dict):
        data = {"value": data}
    tool = data.get("tool", "")
    ok_value = data.get("ok")
    if ok_value is True:
        status = '<span class="ok">ok</span>'
    elif ok_value is False:
        status = '<span class="fail">failed</span>'
    else:
        status = ""
    data_json = json.dumps(data, ensure_ascii=False, indent=2, default=str)
    return (
        "      <tr>"
        f"<td>{index}</td>"
        f"<td>{escape(str(event.get('timestamp', '')))}</td>"
        f"<td>{escape(str(event.get('event', 'unknown')))}</td>"
        f"<td>{escape(str(tool))}</td>"
        f"<td>{status}</td>"
        f"<td><pre>{escape(data_json)}</pre></td>"
        "</tr>"
    )
