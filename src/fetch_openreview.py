"""Fetch public metadata from OpenReview."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import requests

from config import MAX_PAPERS, OPENREVIEW_BASE_URL


def _content_value(content: dict[str, Any], key: str, default: Any = "") -> Any:
    value = content.get(key, default)
    if isinstance(value, dict) and "value" in value:
        return value.get("value", default)
    return value


def _year_from_millis(value: int | None) -> int | None:
    if not value:
        return None
    try:
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc).year
    except (OSError, ValueError):
        return None


def _paper_from_note(note: dict[str, Any], keyword: str) -> dict[str, Any]:
    content = note.get("content") or {}
    note_id = note.get("id") or note.get("forum") or ""
    title = _content_value(content, "title", "Untitled")
    abstract = _content_value(content, "abstract", "")
    authors = _content_value(content, "authors", [])
    if isinstance(authors, str):
        authors = [authors]
    venue = _content_value(content, "venue", "") or _content_value(content, "venueid", "") or "OpenReview"
    pdf = _content_value(content, "pdf", "")
    pdf_url = f"https://openreview.net{pdf}" if isinstance(pdf, str) and pdf.startswith("/") else pdf

    return {
        "paper_id": f"openreview:{note_id}",
        "source_type": "openreview",
        "title": title,
        "authors": authors if isinstance(authors, list) else [],
        "publication_year": _year_from_millis(note.get("cdate") or note.get("pdate")),
        "published_date": "",
        "cited_by_count": 0,
        "abstract": abstract,
        "doi": "",
        "url": f"https://openreview.net/forum?id={note_id}" if note_id else "",
        "pdf_url": pdf_url or "",
        "venue": venue,
        "venue_type": "conference/review",
        "is_open_access": True,
        "matched_keyword": keyword,
        "source_metrics": {},
    }


def fetch_openreview_papers(
    keywords: list[str],
    max_papers: int = MAX_PAPERS,
) -> list[dict[str, Any]]:
    """Search OpenReview notes by keyword."""

    papers: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for keyword in keywords:
        try:
            response = requests.get(
                f"{OPENREVIEW_BASE_URL}/notes/search",
                params={
                    "term": keyword,
                    "content": "all",
                    "source": "forum",
                    "sort": "tmdate:desc",
                    "limit": max(1, min(max_papers, 50)),
                },
                headers={"User-Agent": "paper-agent/0.1"},
                timeout=25,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            print(f"[OpenReview] Failed to fetch keyword '{keyword}': {exc}")
            continue

        for note in response.json().get("notes", []):
            paper = _paper_from_note(note, keyword)
            paper_id = str(paper.get("paper_id") or "")
            if not paper_id or paper_id in seen_ids:
                continue
            seen_ids.add(paper_id)
            papers.append(paper)

    return papers
