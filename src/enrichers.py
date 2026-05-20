"""Free metadata enrichment helpers for candidate papers."""

from __future__ import annotations

import re
from typing import Any

import requests

from config import (
    CROSSREF_BASE_URL,
    ENABLE_CROSSREF,
    ENABLE_SEMANTIC_SCHOLAR,
    ENABLE_UNPAYWALL,
    SEMANTIC_SCHOLAR_API_KEY,
    SEMANTIC_SCHOLAR_BASE_URL,
    UNPAYWALL_BASE_URL,
    UNPAYWALL_EMAIL,
)


def _headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    headers = {"User-Agent": "paper-agent/0.1"}
    if extra:
        headers.update(extra)
    return headers


def _semantic_headers() -> dict[str, str]:
    headers = _headers()
    if SEMANTIC_SCHOLAR_API_KEY:
        headers["x-api-key"] = SEMANTIC_SCHOLAR_API_KEY
    return headers


def _normalize_doi(doi: str | None) -> str:
    if not doi:
        return ""
    doi = doi.strip()
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi, flags=re.I)
    return doi.strip()


def enrich_with_crossref(paper: dict[str, Any]) -> dict[str, Any]:
    doi = _normalize_doi(paper.get("doi"))
    if not ENABLE_CROSSREF or not doi:
        return paper

    try:
        response = requests.get(
            f"{CROSSREF_BASE_URL}/{doi}",
            headers=_headers(),
            timeout=20,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"[Crossref] Failed to enrich DOI '{doi}': {exc}")
        return paper

    message = response.json().get("message") or {}
    container = message.get("container-title") or []
    subjects = message.get("subject") or []
    published = message.get("published-print") or message.get("published-online") or {}
    date_parts = published.get("date-parts") or []
    year = date_parts[0][0] if date_parts and date_parts[0] else None

    paper["doi"] = doi
    paper["crossref"] = {
        "publisher": message.get("publisher") or "",
        "type": message.get("type") or "",
        "subject": subjects,
        "reference_count": message.get("reference-count"),
        "is_referenced_by_count": message.get("is-referenced-by-count"),
        "url": message.get("URL") or "",
    }
    if not paper.get("venue") and container:
        paper["venue"] = container[0]
    if not paper.get("publication_year") and year:
        paper["publication_year"] = year
    if message.get("is-referenced-by-count"):
        paper["cited_by_count"] = max(
            int(paper.get("cited_by_count") or 0),
            int(message.get("is-referenced-by-count") or 0),
        )
    if message.get("URL") and not paper.get("url"):
        paper["url"] = message["URL"]
    return paper


def enrich_with_unpaywall(paper: dict[str, Any]) -> dict[str, Any]:
    doi = _normalize_doi(paper.get("doi"))
    if not ENABLE_UNPAYWALL or not doi or not UNPAYWALL_EMAIL:
        return paper

    try:
        response = requests.get(
            f"{UNPAYWALL_BASE_URL}/{doi}",
            params={"email": UNPAYWALL_EMAIL},
            headers=_headers(),
            timeout=20,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"[Unpaywall] Failed to enrich DOI '{doi}': {exc}")
        return paper

    data = response.json()
    best = data.get("best_oa_location") or {}
    pdf_url = best.get("url_for_pdf") or ""
    landing_url = best.get("url") or ""

    paper["unpaywall"] = {
        "is_oa": data.get("is_oa"),
        "oa_status": data.get("oa_status"),
        "best_oa_pdf_url": pdf_url,
        "best_oa_url": landing_url,
        "license": best.get("license") or "",
        "host_type": best.get("host_type") or "",
    }
    if data.get("is_oa"):
        paper["is_open_access"] = True
    if pdf_url and not paper.get("oa_pdf_url"):
        paper["oa_pdf_url"] = pdf_url
    if landing_url and not paper.get("url"):
        paper["url"] = landing_url
    return paper


def enrich_with_semantic_scholar(paper: dict[str, Any]) -> dict[str, Any]:
    if not ENABLE_SEMANTIC_SCHOLAR:
        return paper

    doi = _normalize_doi(paper.get("doi"))
    arxiv_id = paper.get("arxiv_id")
    paper_key = f"DOI:{doi}" if doi else f"ARXIV:{arxiv_id}" if arxiv_id else ""
    if not paper_key:
        return paper

    try:
        response = requests.get(
            f"{SEMANTIC_SCHOLAR_BASE_URL}/paper/{paper_key}",
            params={
                "fields": "paperId,url,venue,year,citationCount,influentialCitationCount,isOpenAccess,openAccessPdf,fieldsOfStudy,publicationTypes,externalIds,tldr"
            },
            headers=_semantic_headers(),
            timeout=20,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"[Semantic Scholar] Failed to enrich paper '{paper_key}': {exc}")
        return paper

    data = response.json()
    open_pdf = data.get("openAccessPdf") or {}
    tldr = data.get("tldr") or {}
    paper["semantic_scholar"] = {
        "paper_id": data.get("paperId"),
        "url": data.get("url"),
        "citation_count": data.get("citationCount"),
        "influential_citation_count": data.get("influentialCitationCount"),
        "fields_of_study": data.get("fieldsOfStudy") or [],
        "publication_types": data.get("publicationTypes") or [],
        "tldr": tldr.get("text") or "",
    }
    paper["cited_by_count"] = max(
        int(paper.get("cited_by_count") or 0),
        int(data.get("citationCount") or 0),
    )
    paper["influential_citation_count"] = max(
        int(paper.get("influential_citation_count") or 0),
        int(data.get("influentialCitationCount") or 0),
    )
    if data.get("isOpenAccess") or open_pdf.get("url"):
        paper["is_open_access"] = True
    if open_pdf.get("url") and not paper.get("oa_pdf_url"):
        paper["oa_pdf_url"] = open_pdf["url"]
    if data.get("url") and not paper.get("url"):
        paper["url"] = data["url"]
    if tldr.get("text") and not paper.get("abstract"):
        paper["abstract"] = tldr["text"]
    return paper


def enrich_papers(papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Apply low-volume free enrichment APIs to a short candidate list."""

    enriched = []
    for paper in papers:
        item = dict(paper)
        item = enrich_with_crossref(item)
        item = enrich_with_unpaywall(item)
        item = enrich_with_semantic_scholar(item)
        enriched.append(item)
    return enriched
