"""JSONL trace writer for agent runs.

One file per run. Each line is a JSON record with kind ∈ {run_meta, tool_call,
tool_result, model_input, model_output, final}. Trace files are designed for
replay: every tool call records args, every tool result records output.
"""

from __future__ import annotations

import json
import time
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterator


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


@dataclass
class TurnRecord:
    run_id: str
    turn: int
    ts: str
    kind: str
    payload: dict[str, Any]


class TraceWriter:
    def __init__(self, path: Path, run_id: str, meta: dict[str, Any] | None = None):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.run_id = run_id
        self.turn = 0
        self._fh = self.path.open("w")
        self._write("run_meta", meta or {})

    def _write(self, kind: str, payload: dict[str, Any]) -> None:
        rec = TurnRecord(
            run_id=self.run_id,
            turn=self.turn,
            ts=_now_iso(),
            kind=kind,
            payload=payload,
        )
        self._fh.write(json.dumps(asdict(rec), default=str) + "\n")
        self._fh.flush()
        self.turn += 1

    def tool_call(self, name: str, args: dict[str, Any]) -> None:
        self._write("tool_call", {"name": name, "args": args})

    def tool_result(self, name: str, result: Any) -> None:
        self._write("tool_result", {"name": name, "result": result})

    def model_input(self, messages: list[dict[str, Any]]) -> None:
        self._write("model_input", {"messages": messages})

    def model_output(self, output: Any) -> None:
        self._write("model_output", {"output": output})

    def final(
        self,
        predicted_sql: str | None = None,
        success: bool = True,
        error: str | None = None,
    ) -> None:
        self._write(
            "final",
            {"predicted_sql": predicted_sql, "success": success, "error": error},
        )

    def close(self) -> None:
        self._fh.close()


@contextmanager
def open_trace(
    path: Path, meta: dict[str, Any] | None = None
) -> Iterator[TraceWriter]:
    run_id = str(uuid.uuid4())
    writer = TraceWriter(path, run_id, meta)
    try:
        yield writer
    finally:
        writer.close()
