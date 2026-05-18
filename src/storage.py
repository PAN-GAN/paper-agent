"""Persistent sent-paper records."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import DATA_DIR, SENT_PAPERS_FILE


def ensure_storage(path: Path = SENT_PAPERS_FILE) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("[]\n", encoding="utf-8")


def load_sent_records(path: Path = SENT_PAPERS_FILE) -> list[dict[str, Any]]:
    ensure_storage(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        print(f"[Storage] Invalid JSON in {path}. Reinitializing.")
        path.write_text("[]\n", encoding="utf-8")
        return []


def load_sent_ids(path: Path = SENT_PAPERS_FILE) -> set[str]:
    return {
        str(record.get("paper_id"))
        for record in load_sent_records(path)
        if record.get("paper_id")
    }


def mark_as_sent(paper: dict[str, Any], path: Path = SENT_PAPERS_FILE) -> None:
    records = load_sent_records(path)
    paper_id = str(paper.get("paper_id") or "")
    if paper_id and any(str(record.get("paper_id")) == paper_id for record in records):
        return

    records.append(
        {
            "paper_id": paper_id,
            "title": paper.get("title") or "",
            "url": paper.get("url") or paper.get("pdf_url") or "",
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    path.write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
