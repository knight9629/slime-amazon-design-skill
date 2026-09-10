from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any


HARD_MAX_CHILD_WORKERS = 3
TRANSPORT_ERROR_TYPES = {
    "AUTH",
    "NETWORK",
    "RATE_LIMIT",
    "TIMEOUT",
    "TRANSPORT",
}


def refill_ready_slots(
    pending: list[str],
    running: list[str],
    *,
    completed_slot_id: str | None = None,
    capacity: int = HARD_MAX_CHILD_WORKERS,
) -> dict[str, list[str]]:
    """Complete one slot and immediately refill every open image lane."""
    if capacity < 1 or capacity > HARD_MAX_CHILD_WORKERS:
        raise ValueError(f"capacity must be between 1 and {HARD_MAX_CHILD_WORKERS}")
    if len(set(pending + running)) != len(pending) + len(running):
        raise ValueError("pending and running slot ids must be unique")
    next_pending = list(pending)
    next_running = list(running)
    if completed_slot_id is not None:
        if completed_slot_id not in next_running:
            raise ValueError(f"completed slot is not running: {completed_slot_id}")
        next_running.remove(completed_slot_id)
    opened: list[str] = []
    while next_pending and len(next_running) < capacity:
        slot_id = next_pending.pop(0)
        next_running.append(slot_id)
        opened.append(slot_id)
    return {
        "pending": next_pending,
        "running": next_running,
        "opened": opened,
    }


def is_transport_error(record: dict[str, Any]) -> bool:
    status = str(record.get("status", "")).strip().upper()
    error_type = str(record.get("error_type", "")).strip().upper()
    return status in {"FAILED", "ERROR", "BLOCKED"} and (
        error_type in TRANSPORT_ERROR_TYPES
        or record.get("transport_error") is True
    )


def recommend_workers(
    records: list[dict[str, Any]], *, run_identity: str | None = None
) -> dict[str, Any]:
    if run_identity:
        records = [record for record in records if record.get("run_identity") == run_identity]
    image2_records = [
        record for record in records if record.get("provider") == "image2"
    ]
    transport_error_streak = 0
    for record in reversed(image2_records):
        if is_transport_error(record):
            transport_error_streak += 1
            continue
        break
    workers = (
        1
        if transport_error_streak >= 2
        else 2
        if transport_error_streak == 1
        else HARD_MAX_CHILD_WORKERS
    )
    level = (
        "RECOVERY_ONE_LANE"
        if workers == 1
        else "RECOVERY_TWO_LANE"
        if workers == 2
        else "THREE_LANE"
    )
    return {
        "version": 1,
        "recommended_child_workers": workers,
        "hard_max_child_workers": HARD_MAX_CHILD_WORKERS,
        "congestion_level": level,
        "reason": (
            "Use all three image lanes; successful latency alone never reduces concurrency."
            if workers == 3
            else f"Temporarily reduced after {transport_error_streak} consecutive transport error(s)."
        ),
        "transport_error_streak": transport_error_streak,
    }


def atomic_write(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Set phase-boundary image2 child concurrency."
    )
    parser.add_argument("--project-root", required=True, type=Path)
    args = parser.parse_args()
    root = args.project_root.expanduser().resolve()
    records = []
    ledger = root / "generation_ledger.jsonl"
    if ledger.is_file():
        for line in ledger.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(json.loads(line))
    active_run = root / "active_run.json"
    run_identity = "legacy-unscoped"
    if active_run.is_file():
        active_data = json.loads(active_run.read_text(encoding="utf-8"))
        run_identity = str(active_data.get("run_identity", "")).strip() or "legacy-unscoped"
    filtered_records = (
        [record for record in records if record.get("run_identity") == run_identity]
        if run_identity
        else records
    )
    state = recommend_workers(records, run_identity=run_identity)
    state["policy"] = "PHASE_BOUNDARY_SCHEDULER"
    state["phase"] = "IMAGE_GENERATION"
    state["run_identity"] = run_identity
    state["evidence_record_count"] = len(filtered_records)
    state["evidence_ledger_sha256"] = (
        hashlib.sha256(ledger.read_bytes()).hexdigest() if ledger.is_file() else None
    )
    atomic_write(root / "scheduler_state.json", state)
    print(json.dumps(state, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
