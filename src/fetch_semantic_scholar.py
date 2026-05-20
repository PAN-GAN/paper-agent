"""Fetch public paper metadata from Semantic Scholar."""

from __future__ import annotations

from typing import Any

import requests

from config import MAX_PAPERS, SEMANTIC_SCHOLAR_API_KEY, SEMANTIC_SCHOLAR_BASE_URL


FIELDS = ",".join(
    [
        "paperId",
        "title",
        "authors",
        "year",
        "abstract",
        "url",
        "venue",
        "citationCount",
        "influentialCitationCount",
        "isOpenAccess",
        "openAccessPdf",
        "externalIds",
        "fieldsOfStudy",
        "publicationTypes",
        "publicationDate",
        "tldr",
    ]
)


def _headers() -> dict[str, str]:
    headers = {"User-Agent": "paper-agent/0.1"}
    if SEMANTIC_SCHOLAR_API_KEY:
        headers["x-api-key"] = SEMANTIC_SCHOLAR_API_KEY
    return headers


def _paper_from_result(item: dict[str, Any], keyword: str) -> dict[str, Any]:
    external_ids = item.get("externalIds") or {}
    doi = external_ids.get("DOI") or ""
    arxiv_id = external_ids.get("ArXiv") or ""
    open_pdf = item.get("openAccessPdf") or {}
    tldr = item.get("tldr") or {}

    return {
        "paper_id": item.get("paperId") or doi or item.get("url") or item.get("title", ""),
        "source_type": "semantic_scholar",
        "title": item.get("title") or "Untitled",
        "authors": [author.get("name") for author in item.get("authors", []) if author.get("name")],
        "publication_year": item.get("year"),
        "published_date": item.get("publicationDate") or "",
        "cited_by_count": item.get("citationCount") or 0,
        "influential_citation_count": item.get("influentialCitationCount") or 0,
        "abstract": item.get("abstract") or tldr.get("text") or "",
        "doi": doi,
        "arxiv_id": arxiv_id,
        "url": item.get("url") or (f"https://doi.org/{doi}" if doi else ""),
        "venue": item.get("venue") or "Semantic Scholar",
        "venue_type": "",
        "fields_of_study": item.get("fieldsOfStudy") or [],
        "publication_types": item.get("publicationTypes") or [],
        "is_open_access": bool(item.get("isOpenAccess") or open_pdf.get("url")),
        "oa_pdf_url": open_pdf.get("url") or "",
        "matched_keyword": keyword,
        "source_metrics": {},
    }


def fetch_semantic_scholar_papers(
    keywords: list[str],
    max_papers: int = MAX_PAPERS,
) -> list[dict[str, Any]]:
    """Search Semantic Scholar by keywords and return normalized papers."""

    papers: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for keyword in keywords:
        try:
            response = requests.get(
                f"{SEMANTIC_SCHOLAR_BASE_URL}/paper/search",
                params={
                    "query": keyword,
                    "limit": max(1, min(max_papers, 50)),
                    "fields": FIELDS,
                },
                headers=_headers(),
                timeout=25,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            print(f"[Semantic Scholar] Failed to fetch keyword '{keyword}': {exc}")
            continue

        for item in response.json().get("data", []):
            paper = _paper_from_result(item, keyword)
            paper_id = str(paper.get("paper_id") or "")
            if not paper_id or paper_id in seen_ids:
                continue
            seen_ids.add(paper_id)
            papers.append(paper)

    return papers
