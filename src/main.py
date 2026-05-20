"""Daily entry point for the personal research intelligence agent."""

from __future__ import annotations

from config import ENABLE_ARXIV, ENABLE_OPENALEX, KEYWORDS, MAX_PAPERS
from fetch_arxiv import fetch_arxiv_papers
from fetch_openalex import fetch_openalex_papers
from notifier_email import send_email
from scorer import choose_best_paper
from storage import ensure_storage, load_sent_ids, mark_as_sent
from summarizer_deepseek import summarize_paper


def main() -> int:
    ensure_storage()
    sent_ids = load_sent_ids()
    print(f"[Main] Loaded {len(sent_ids)} sent paper records.")

    openalex_papers = []
    arxiv_papers = []

    if ENABLE_OPENALEX:
        print("[Main] Fetching OpenAlex papers...")
        openalex_papers = fetch_openalex_papers(KEYWORDS, MAX_PAPERS)
        print(f"[Main] OpenAlex candidates: {len(openalex_papers)}")

    if ENABLE_ARXIV:
        print("[Main] Fetching arXiv papers...")
        arxiv_papers = fetch_arxiv_papers(KEYWORDS, MAX_PAPERS)
        print(f"[Main] arXiv candidates: {len(arxiv_papers)}")

    paper = choose_best_paper(openalex_papers, arxiv_papers, sent_ids)
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
