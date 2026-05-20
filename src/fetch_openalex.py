"""Fetch public paper metadata from OpenAlex."""

from __future__ import annotations

from datetime import date
from typing import Any

import requests

from config import MAX_PAPERS, OPENALEX_BASE_URL, OPENALEX_MAILTO, OPENALEX_SOURCES_BASE_URL


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


def _source_api_url(source_id: str) -> str:
    if source_id.startswith("https://openalex.org/"):
        return source_id.replace("https://openalex.org/", "https://api.openalex.org/", 1)
    if source_id.startswith("S"):
        return f"{OPENALEX_SOURCES_BASE_URL}/{source_id}"
    return source_id


def _fetch_source_metrics(
    source_id: str,
    headers: dict[str, str],
    cache: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if not source_id:
        return {}
    if source_id in cache:
        return cache[source_id]

    params: dict[str, str] = {
        "select": "id,display_name,type,summary_stats,works_count,cited_by_count,is_core,is_in_doaj,is_oa"
    }
    if OPENALEX_MAILTO:
        params["mailto"] = OPENALEX_MAILTO

    try:
        response = requests.get(_source_api_url(source_id), params=params, headers=headers, timeout=15)
        response.raise_for_status()
        source = response.json()
    except requests.RequestException as exc:
        print(f"[OpenAlex] Failed to fetch source metrics '{source_id}': {exc}")
        cache[source_id] = {}
        return {}

    stats = source.get("summary_stats") or {}
    metrics = {
        "source_display_name": source.get("display_name") or "",
        "source_type": source.get("type") or "",
        "two_year_mean_citedness": stats.get("2yr_mean_citedness"),
        "h_index": stats.get("h_index"),
        "i10_index": stats.get("i10_index"),
        "works_count": source.get("works_count"),
        "source_cited_by_count": source.get("cited_by_count"),
        "is_core": source.get("is_core"),
        "is_in_doaj": source.get("is_in_doaj"),
        "is_oa_source": source.get("is_oa"),
        "metric_note": "OpenAlex 2-year mean citedness is an open Impact-Factor-like metric, not JCR IF.",
    }
    cache[source_id] = metrics
    return metrics


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

    source_id = source.get("id") or ""
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
        "source_id": source_id,
        "venue": source.get("display_name") or "OpenAlex",
        "venue_type": source.get("type") or "",
        "is_open_access": bool(open_access.get("is_oa")),
        "oa_status": open_access.get("oa_status") or "",
        "matched_keyword": keyword,
    }


def fetch_openalex_papers(keywords: list[str], max_papers: int = MAX_PAPERS) -> list[dict[str, Any]]:
    """Search OpenAlex by keywords and return normalized paper dictionaries."""

    papers: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    source_metrics_cache: dict[str, dict[str, Any]] = {}
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
            source_id = str(paper.get("source_id") or "")
            paper["source_metrics"] = _fetch_source_metrics(source_id, headers, source_metrics_cache)
            seen_ids.add(paper_id)
            papers.append(paper)

    return papers
