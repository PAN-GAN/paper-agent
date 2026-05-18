"""Fetch recent public preprint metadata from arXiv."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any
from urllib.parse import urlencode

import requests

from config import ARXIV_BASE_URL, MAX_PAPERS


ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}
ARXIV_NS = {"arxiv": "http://arxiv.org/schemas/atom"}


def _text(element: ET.Element | None) -> str:
    return (element.text or "").strip() if element is not None else ""


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _entry_to_paper(entry: ET.Element, keyword: str) -> dict[str, Any]:
    arxiv_url = _text(entry.find("atom:id", ATOM_NS))
    pdf_url = ""
    for link in entry.findall("atom:link", ATOM_NS):
        if link.attrib.get("title") == "pdf" or link.attrib.get("type") == "application/pdf":
            pdf_url = link.attrib.get("href", "")
            break

    authors = [
        _text(author.find("atom:name", ATOM_NS))
        for author in entry.findall("atom:author", ATOM_NS)
    ]
    authors = [author for author in authors if author]

    category_node = entry.find("arxiv:primary_category", ARXIV_NS)
    category = category_node.attrib.get("term", "") if category_node is not None else ""
    published_date = _text(entry.find("atom:published", ATOM_NS))
    year = None
    if published_date[:4].isdigit():
        year = int(published_date[:4])

    return {
        "paper_id": arxiv_url or _text(entry.find("atom:title", ATOM_NS)),
        "source_type": "arxiv",
        "title": _normalize_whitespace(_text(entry.find("atom:title", ATOM_NS))) or "Untitled",
        "authors": authors,
        "publication_year": year,
        "published_date": published_date,
        "cited_by_count": 0,
        "abstract": _normalize_whitespace(_text(entry.find("atom:summary", ATOM_NS))),
        "doi": "",
        "url": arxiv_url,
        "arxiv_url": arxiv_url,
        "pdf_url": pdf_url,
        "venue": "arXiv",
        "category": category,
        "is_open_access": True,
        "oa_status": "arxiv",
        "matched_keyword": keyword,
    }


def fetch_arxiv_papers(keywords: list[str], max_papers: int = MAX_PAPERS) -> list[dict[str, Any]]:
    """Search arXiv by keywords and return normalized paper dictionaries."""

    papers: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for keyword in keywords:
        query = urlencode(
            {
                "search_query": f'all:"{keyword}"',
                "start": 0,
                "max_results": max(1, min(max_papers, 50)),
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            }
        )
        try:
            response = requests.get(f"{ARXIV_BASE_URL}?{query}", timeout=25)
            response.raise_for_status()
            root = ET.fromstring(response.text)
        except (requests.RequestException, ET.ParseError) as exc:
            print(f"[arXiv] Failed to fetch keyword '{keyword}': {exc}")
            continue

        for entry in root.findall("atom:entry", ATOM_NS):
            paper = _entry_to_paper(entry, keyword)
            paper_id = str(paper.get("paper_id") or "")
            if not paper_id or paper_id in seen_ids:
                continue
            seen_ids.add(paper_id)
            papers.append(paper)

    return papers
