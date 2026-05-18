"""Fetch public paper metadata from OpenAlex."""

from __future__ import annotations

from datetime import date
from typing import Any

import requests

from config import MAX_PAPERS, OPENALEX_BASE_URL, OPENALEX_MAILTO


def _abstract_from_inverted_index(index: dict[str, list[int]] | None) -> str:
    if not index:
        return ""

    words: list[tuple[int, str]] = []
    for word, positions in index.items():
        for position in positions:
            words.append((position, word))
    words.sort(key=lambda item: item[0])
    return " ".join(word for _, word in words)


def _clean_authors(work: dict[str, Any]) -> list[str]:
    authors = []
    for authorship in work.get("authorships", []):
        author = authorship.get("author") or {}
        name = author.get("display_name")
        if name:
            authors.append(name)
    return authors


def _paper_from_work(work: dict[str, Any], keyword: str) -> dict[str, Any]:
    primary_location = work.get("primary_location") or {}
    source = primary_location.get("source") or {}
    open_access = work.get("open_access") or {}

    doi = work.get("doi") or ""
    url = (
        primary_location.get("landing_page_url")
        or work.get("id")
        or doi
        or ""
    )

    return {
        "paper_id": work.get("id") or doi or work.get("title", ""),
        "source_type": "openalex",
        "title": work.get("title") or "Untitled",
        "authors": _clean_authors(work),
        "publication_year": work.get("publication_year"),
        "published_date": work.get("publication_date") or "",
        "cited_by_count": work.get("cited_by_count") or 0,
        "abstract": _abstract_from_inverted_index(work.get("abstract_inverted_index")),
        "doi": doi,
        "url": url,
        "venue": source.get("display_name") or "OpenAlex",
        "is_open_access": bool(open_access.get("is_oa")),
        "oa_status": open_access.get("oa_status") or "",
        "matched_keyword": keyword,
    }


def fetch_openalex_papers(keywords: list[str], max_papers: int = MAX_PAPERS) -> list[dict[str, Any]]:
    """Search OpenAlex by keywords and return normalized paper dictionaries."""

    papers: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    current_year = date.today().year
    from_year = current_year - 5

    headers = {"User-Agent": "paper-agent/0.1"}
    params_base: dict[str, str | int] = {
        "per-page": max(1, min(max_papers, 50)),
        "sort": "cited_by_count:desc",
        "filter": f"from_publication_date:{from_year}-01-01",
    }
    if OPENALEX_MAILTO:
        params_base["mailto"] = OPENALEX_MAILTO

    for keyword in keywords:
        params = dict(params_base)
        params["search"] = keyword
        try:
            response = requests.get(
                OPENALEX_BASE_URL,
                params=params,
                headers=headers,
                timeout=25,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            print(f"[OpenAlex] Failed to fetch keyword '{keyword}': {exc}")
            continue

        for work in response.json().get("results", []):
            paper = _paper_from_work(work, keyword)
            paper_id = str(paper.get("paper_id") or "")
            if not paper_id or paper_id in seen_ids:
                continue
            seen_ids.add(paper_id)
            papers.append(paper)

    return papers
