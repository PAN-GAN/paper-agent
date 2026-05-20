"""Merge duplicate papers returned by multiple free data sources."""

from __future__ import annotations

import re
from typing import Any


def _normalize_doi(doi: str | None) -> str:
    if not doi:
        return ""
    doi = doi.strip().lower()
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi)
    return doi


def _normalize_title(title: str | None) -> str:
    if not title:
        return ""
    return re.sub(r"\W+", " ", title.lower()).strip()


def paper_key(paper: dict[str, Any]) -> str:
    doi = _normalize_doi(paper.get("doi"))
    if doi:
        return f"doi:{doi}"
    arxiv_id = paper.get("arxiv_id")
    if arxiv_id:
        return f"arxiv:{str(arxiv_id).lower()}"
    title = _normalize_title(paper.get("title"))
    return f"title:{title}" if title else str(paper.get("paper_id") or "")


def _merge_lists(left: list[Any], right: list[Any]) -> list[Any]:
    merged = []
    seen = set()
    for item in [*left, *right]:
        key = str(item).lower()
        if key and key not in seen:
            seen.add(key)
            merged.append(item)
    return merged


def merge_papers(papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}

    for paper in papers:
        key = paper_key(paper)
        if not key:
            continue
        if key not in merged:
            item = dict(paper)
            item["source_types"] = [paper.get("source_type", "unknown")]
            merged[key] = item
            continue

        current = merged[key]
        current["source_types"] = _merge_lists(
            current.get("source_types", []),
            [paper.get("source_type", "unknown")],
        )
        for field in [
            "abstract",
            "doi",
            "url",
            "pdf_url",
            "oa_pdf_url",
            "venue",
            "venue_type",
            "published_date",
            "matched_keyword",
        ]:
            if not current.get(field) and paper.get(field):
                current[field] = paper[field]
        if paper.get("publication_year") and not current.get("publication_year"):
            current["publication_year"] = paper["publication_year"]
        current["authors"] = _merge_lists(current.get("authors", []), paper.get("authors", []))
        current["cited_by_count"] = max(
            int(current.get("cited_by_count") or 0),
            int(paper.get("cited_by_count") or 0),
        )
        current["influential_citation_count"] = max(
            int(current.get("influential_citation_count") or 0),
            int(paper.get("influential_citation_count") or 0),
        )
        current["is_open_access"] = bool(current.get("is_open_access") or paper.get("is_open_access"))
        if paper.get("source_metrics") and not current.get("source_metrics"):
            current["source_metrics"] = paper["source_metrics"]

    return list(merged.values())
