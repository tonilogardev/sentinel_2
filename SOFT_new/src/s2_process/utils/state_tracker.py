"""State tracker — generates segments from date range + orbits, persists state."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


STATE_STEPS = [
    "downloaded",
    "l1c_processed",
    "l2a_generated",
    "l2a_processed",
    "quicklook",
    "l2a_demcat_generated",
    "l2a_demcat_processed",
]


def _dates_in_range(start: str, end: str) -> list[str]:
    s = datetime.strptime(start, "%Y-%m-%d")
    e = datetime.strptime(end, "%Y-%m-%d")
    return [(s + timedelta(days=d)).strftime("%Y-%m-%d") for d in range((e - s).days + 1)]


def _segment_id(date: str, orbit: str, satellite: str = "A") -> str:
    return f"{date}_{orbit}_{satellite}"


def _empty_state() -> dict[str, str | None]:
    return {step: None for step in STATE_STEPS}


class StateTracker:
    def __init__(self, state_path: str | Path | None = None):
        self.state_path = Path(state_path) if state_path else None
        self.segments: list[dict[str, Any]] = []
        self._dates: list[str] = []
        self._orbits: list[str] = []

    @classmethod
    def from_config(cls, config: dict[str, Any], state_path: str | Path | None = None) -> "StateTracker":
        obj = cls(state_path)

        dr = config.get("dateRange", {})
        obj._dates = _dates_in_range(dr.get("start"), dr.get("end"))
        obj._orbits = config.get("orbits", [])

        saved = config.get("segments", [])
        saved_map = {_segment_id(s["date"], s["orbit"], s.get("satellite", "A")): s["state"] for s in saved}

        for date in obj._dates:
            for orbit in obj._orbits:
                key = _segment_id(date, orbit)
                state = saved_map.get(key, deepcopy(_empty_state()))
                obj.segments.append({"date": date, "orbit": orbit, "satellite": "A", "state": state})

        return obj

    @classmethod
    def from_file(cls, path: str | Path, config: dict[str, Any]) -> "StateTracker":
        path = Path(path)
        if not path.exists():
            return cls.from_config(config, path)
        with open(path) as f:
            data = json.load(f)
        merged = deepcopy(config)
        merged["segments"] = data.get("segments", [])
        return cls.from_config(merged, path)

    def to_dict(self) -> dict:
        return {"segments": self.segments}

    def save(self, path: str | Path | None = None) -> None:
        p = Path(path) if path else self.state_path
        if p:
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "w") as f:
                json.dump(self.to_dict(), f, indent=2)

    def first_pending(self) -> dict[str, Any] | None:
        for seg in self.segments:
            if self.next_step(seg) is not None:
                return seg
        return None

    def next_step(self, segment: dict[str, Any]) -> str | None:
        state = segment.get("state", {})
        for step in STATE_STEPS:
            if state.get(step) is None:
                return step
        return None

    def mark(self, segment: dict[str, Any], step: str, value: str = "*") -> None:
        sid = _segment_id(segment["date"], segment["orbit"], segment.get("satellite", "A"))
        for seg in self.segments:
            if _segment_id(seg["date"], seg["orbit"], seg.get("satellite", "A")) == sid:
                seg.setdefault("state", {})[step] = value
                break

    def remaining_steps(self, segment: dict[str, Any], after: str | None = None) -> list[str]:
        state = segment.get("state", {})
        started = False
        steps: list[str] = []
        for s in STATE_STEPS:
            if after is None:
                started = True
            if s == after:
                started = True
                continue
            if started and state.get(s) is None:
                steps.append(s)
        return steps

    def all_done(self) -> bool:
        return self.first_pending() is None
