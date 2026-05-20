"""Daily entry point for the personal research intelligence agent."""

from __future__ import annotations

from config import (
    ENABLE_ARXIV,
    ENABLE_OPENALEX,
    ENABLE_OPENREVIEW,
    ENABLE_SEMANTIC_SCHOLAR,
    ENRICH_TOP_N,
    KEYWORDS,
    MAX_PAPERS,
)
from enrichers import enrich_papers
from fetch_arxiv import fetch_arxiv_papers
from fetch_openalex import fetch_openalex_papers
from fetch_openreview import fetch_openreview_papers
from fetch_semantic_scholar import fetch_semantic_scholar_papers
from notifier_email import send_email
from paper_merge import merge_papers
from scorer import choose_best_paper, rank_papers
from storage import ensure_storage, load_sent_ids, mark_as_sent
from summarizer_deepseek import summarize_paper


def main() -> int:
    ensure_storage()
    sent_ids = load_sent_ids()
    print(f"[Main] Loaded {len(sent_ids)} sent paper records.")
    print(f"[Main] Keywords: {', '.join(KEYWORDS)}")

    candidates = []

    if ENABLE_OPENALEX:
        print("[Main] Fetching OpenAlex papers...")
        openalex_papers = fetch_openalex_papers(KEYWORDS, MAX_PAPERS)
        candidates.extend(openalex_papers)
        print(f"[Main] OpenAlex candidates: {len(openalex_papers)}")

    if ENABLE_SEMANTIC_SCHOLAR:
        print("[Main] Fetching Semantic Scholar papers...")
        semantic_papers = fetch_semantic_scholar_papers(KEYWORDS, MAX_PAPERS)
        candidates.extend(semantic_papers)
        print(f"[Main] Semantic Scholar candidates: {len(semantic_papers)}")

    if ENABLE_ARXIV:
        print("[Main] Fetching arXiv papers...")
        arxiv_papers = fetch_arxiv_papers(KEYWORDS, MAX_PAPERS)
        candidates.extend(arxiv_papers)
        print(f"[Main] arXiv candidates: {len(arxiv_papers)}")

    if ENABLE_OPENREVIEW:
        print("[Main] Fetching OpenReview papers...")
        openreview_papers = fetch_openreview_papers(KEYWORDS, MAX_PAPERS)
        candidates.extend(openreview_papers)
        print(f"[Main] OpenReview candidates: {len(openreview_papers)}")

    merged = merge_papers(candidates)
    print(f"[Main] Merged candidates: {len(merged)}")

    prelim_ranked = rank_papers(merged, sent_ids)
    enrich_targets = prelim_ranked[:ENRICH_TOP_N]
    print(f"[Main] Enriching top candidates: {len(enrich_targets)}")
    enriched = enrich_papers(enrich_targets)
    remaining_keys = {paper.get("paper_id") for paper in enrich_targets}
    candidate_pool = enriched + [
        paper for paper in merged if paper.get("paper_id") not in remaining_keys
    ]

    paper = choose_best_paper(candidate_pool, sent_ids)
    if not paper:
        print("[Main] No unsent paper found today.")
        return 0

    print(f"[Main] Selected paper: {paper.get('title')} (score={paper.get('score')})")
    summary = summarize_paper(paper)

    sent = send_email(str(paper.get("title") or "今日优秀论文推荐"), summary, paper)
    if sent:
        mark_as_sent(paper)
        print("[Main] Paper marked as sent.")
    else:
        print("[Main] Notification was not sent. Paper will not be marked as sent.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
