from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RunControlConfig:
    max_seconds: float | None = None
    max_tools: int | None = None
    max_tokens: int | None = None
    repeat_limit: int | None = None
    cancel_file: str | None = None

    def __post_init__(self) -> None:
        for value in (self.max_tools, self.max_tokens, self.repeat_limit):
            if value is not None and (type(value) is not int or value <= 0):
                raise ValueError("Run count limits must be positive integers")
        if self.max_seconds is not None and (
                not math.isfinite(self.max_seconds) or self.max_seconds <= 0):
            raise ValueError("Run time limit must be a positive finite number")
        if self.repeat_limit is not None and self.repeat_limit < 2:
            raise ValueError("No-progress detection requires at least two observations")


class RunControls:
    def __init__(self, config: RunControlConfig, workspace: Path, clock=time.monotonic):
        if config.cancel_file and Path(config.cancel_file).resolve().is_relative_to(workspace.resolve()):
            raise ValueError("Cancellation signal must be outside the Agent workspace")
        self.config, self.clock = config, clock
        self.state: dict[str, Any] = {}

    def policy(self) -> dict[str, Any]:
        return {key: value for key, value in asdict(self.config).items() if value is not None}

    def start(self, saved: dict[str, Any] | None = None) -> None:
        self.state = saved if saved is not None else {
            "elapsed": 0.0, "tools": 0, "input_tokens": 0, "output_tokens": 0,
            "unknown_usage": False, "pending_model": False, "signature": None, "repeats": 0,
        }
        self.last_tick = self.clock()

    def checkpoint(self) -> dict[str, Any]:
        now = self.clock()
        self.state["elapsed"] += max(now - self.last_tick, 0)
        self.last_tick = now
        return self.state

    def reason(self) -> str | None:
        self.checkpoint()
        cfg = self.config
        if cfg.cancel_file and Path(cfg.cancel_file).exists():
            return "cancelled"
        if cfg.max_seconds is not None and self.state["elapsed"] >= cfg.max_seconds:
            return "time_budget"
        if cfg.max_tokens is not None:
            if self.state["pending_model"] or self.state["unknown_usage"]:
                return "token_usage_unknown"
            if self.state["input_tokens"] + self.state["output_tokens"] >= cfg.max_tokens:
                return "token_budget"
        if cfg.repeat_limit is not None and self.state["repeats"] >= cfg.repeat_limit:
            return "no_progress"
        return None

    def dispatch(self, count: int) -> str | None:
        reason = self.reason()
        if reason:
            return reason
        if self.config.max_tools is not None and self.state["tools"] + count > self.config.max_tools:
            return "tool_budget"
        self.state["tools"] += count
        return None

    def response(self, usage: dict[str, int] | None) -> None:
        self.state["pending_model"] = False
        if usage is None:
            self.state["unknown_usage"] = True
        else:
            for key in ("input_tokens", "output_tokens"):
                value = usage.get(key)
                if type(value) is not int or value < 0:
                    self.state["unknown_usage"] = True
                else:
                    self.state[key] += value
        self.checkpoint()

    def observe(self, name: str, arguments: Any, ok: bool, output: str) -> None:
        signature = hashlib.sha256(json.dumps([name, arguments, ok, output], sort_keys=True,
                                              default=str).encode()).hexdigest()
        self.state["repeats"] = self.state["repeats"] + 1 if signature == self.state["signature"] else 1
        self.state["signature"] = signature
        self.checkpoint()
