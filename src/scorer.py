"""Basic paper quality scoring."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from typing import Any

from config import KEYWORDS, MIN_SCORE


HIGH_QUALITY_VENUES = [
    "nature",
    "science",
    "cell",
    "neurips",
    "nips",
    "icml",
    "iclr",
    "acl",
    "emnlp",
    "cvpr",
    "iccv",
    "eccv",
    "aaai",
    "ijcai",
    "kdd",
    "www",
    "sigir",
    "sigmod",
    "vldb",
    "pnas",
    "ieee",
    "acm",
    "remote sensing",
]


@dataclass(frozen=True)
class PaperScore:
    total: float
    citation_score: float
    freshness_score: float
    keyword_score: float
    venue_score: float
    source_metric_score: float
    semantic_score: float
    availability_score: float
    open_access_score: float


def _keyword_matches(paper: dict[str, Any], keywords: list[str]) -> int:
    text = f"{paper.get('title', '')} {paper.get('abstract', '')}".lower()
    return sum(1 for keyword in keywords if keyword.lower() in text)


def score_paper(paper: dict[str, Any], keywords: list[str] | None = None) -> PaperScore:
    """Score a paper with simple, transparent heuristics."""

    keywords = keywords or KEYWORDS
    current_year = date.today().year

    cited_by = int(paper.get("cited_by_count") or 0)
    citation_score = min(math.log1p(cited_by) * 8, 35)

    year = paper.get("publication_year")
    if isinstance(year, int):
        age = max(0, current_year - year)
        freshness_score = max(0, 20 - age * 4)
    else:
        freshness_score = 8

    matches = _keyword_matches(paper, keywords)
    keyword_score = min(matches * 8, 32)
    if paper.get("matched_keyword"):
        keyword_score += 4

    venue = str(paper.get("venue") or "").lower()
    venue_score = 0
    if paper.get("source_type") == "arxiv":
        venue_score = 8
    if any(name in venue for name in HIGH_QUALITY_VENUES):
        venue_score = max(venue_score, 16)

    metrics = paper.get("source_metrics") or {}
    two_year_mean = float(metrics.get("two_year_mean_citedness") or 0)
    h_index = int(metrics.get("h_index") or 0)
    source_metric_score = min(two_year_mean * 2, 8) + min(math.log1p(h_index) * 1.5, 8)

    influential = int(paper.get("influential_citation_count") or 0)
    semantic_score = min(math.log1p(influential) * 4, 12)

    source_types = set(paper.get("source_types") or [paper.get("source_type")])
    availability_score = 0
    if len(source_types) >= 2:
        availability_score += 4
    if paper.get("oa_pdf_url") or paper.get("pdf_url"):
        availability_score += 5
    if paper.get("unpaywall", {}).get("best_oa_pdf_url"):
        availability_score += 3

    open_access_score = 6 if paper.get("is_open_access") else 0

    total = (
        citation_score
        + freshness_score
        + keyword_score
        + venue_score
        + source_metric_score
        + semantic_score
        + availability_score
        + open_access_score
    )
    return PaperScore(
        total=round(total, 2),
        citation_score=round(citation_score, 2),
        freshness_score=round(freshness_score, 2),
        keyword_score=round(keyword_score, 2),
        venue_score=round(venue_score, 2),
        source_metric_score=round(source_metric_score, 2),
        semantic_score=round(semantic_score, 2),
        availability_score=round(availability_score, 2),
        open_access_score=round(open_access_score, 2),
    )


def rank_papers(
    papers: list[dict[str, Any]],
    sent_ids: set[str],
    keywords: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Return unsent papers sorted by score descending."""

    ranked = []
    for paper in papers:
        paper_id = str(paper.get("paper_id") or "")
        if paper_id in sent_ids:
            continue
        score = score_paper(paper, keywords)
        enriched = dict(paper)
        enriched["score"] = score.total
        enriched["score_detail"] = score.__dict__
        ranked.append(enriched)

    return sorted(ranked, key=lambda item: item.get("score", 0), reverse=True)


def choose_best_paper(
    papers: list[dict[str, Any]],
    sent_ids: set[str],
    min_score: float = MIN_SCORE,
) -> dict[str, Any] | None:
    """Choose the highest-scoring unsent paper from a merged candidate pool."""

    ranked = rank_papers(papers, sent_ids)
    if not ranked:
        return None
    if ranked[0]["score"] >= min_score:
        return ranked[0]
    return ranked[0]
