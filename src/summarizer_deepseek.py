"""Generate Chinese paper interpretation with DeepSeek."""

from __future__ import annotations

from typing import Any

import requests

from config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    DEEPSEEK_TIMEOUT_SECONDS,
    KEYWORDS,
)


def _chat_completions_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    return f"{base}/chat/completions"


def _authors_text(paper: dict[str, Any], limit: int = 6) -> str:
    authors = paper.get("authors") or []
    if not authors:
        return "未知"
    visible = authors[:limit]
    suffix = " 等" if len(authors) > limit else ""
    return ", ".join(visible) + suffix


def fallback_summary(paper: dict[str, Any], reason: str | None = None) -> str:
    """Return a useful local summary when the model call is unavailable."""

    reason_text = f"\n\n说明：DeepSeek 调用失败，已生成备用摘要。原因：{reason}" if reason else ""
    abstract = paper.get("abstract") or "暂无摘要。"
    return f"""【今日优秀论文推荐】

标题：{paper.get("title", "未知")}
作者：{_authors_text(paper)}
年份：{paper.get("publication_year") or paper.get("published_date") or "未知"}
来源：{paper.get("venue") or paper.get("source_type") or "未知"}
链接：{paper.get("url") or paper.get("pdf_url") or "无"}

推荐指数：{paper.get("score", "未评分")}
适合方向：{", ".join(KEYWORDS[:4])}

中文摘要：
{abstract}

核心创新点：
1. 可从摘要中提炼研究问题、方法和实验结果。
2. 建议重点关注论文如何定义任务与评估指标。
3. 如有代码或开放数据，可进一步验证方法是否适合复现。

为什么值得读：
这篇论文与当前关注的 AI / 数据科学 / 深度学习方向相关，可作为跟踪研究趋势和积累问题意识的材料。

阅读难度：
中级

复现难度：
中

建议阅读方式：
先看摘要和引言确认问题价值，再看方法图或算法流程，最后阅读实验设置与消融结果。{reason_text}
"""


def summarize_paper(paper: dict[str, Any]) -> str:
    """Call DeepSeek with OpenAI-compatible Chat Completions format."""

    if not DEEPSEEK_API_KEY:
        return fallback_summary(paper, "DEEPSEEK_API_KEY is not configured")

    prompt = f"""
请用中文解读下面这篇论文，面向 AI、数据科学、深度学习学习者。

论文信息：
标题：{paper.get("title")}
作者：{_authors_text(paper)}
年份：{paper.get("publication_year") or paper.get("published_date")}
来源：{paper.get("venue") or paper.get("source_type")}
链接：{paper.get("url") or paper.get("pdf_url")}
推荐分数：{paper.get("score")}
关键词：{paper.get("matched_keyword")}
摘要：{paper.get("abstract")}

请严格使用下面格式输出：

【今日优秀论文推荐】

标题：
作者：
年份：
来源：
链接：

推荐指数：
适合方向：

中文摘要：
用通俗但准确的中文解释论文主要研究了什么。

核心创新点：
1.
2.
3.

为什么值得读：
说明这篇论文对 AI / 数据科学 / 深度学习学习者有什么价值。

阅读难度：
初级 / 中级 / 较难 / 很难

复现难度：
低 / 中 / 高

建议阅读方式：
告诉我应该先看摘要、方法、实验还是代码。
""".strip()

    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "你是一名严谨的中文科研论文解读助手，回答准确、结构清晰、避免夸大。",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
    }

    try:
        response = requests.post(
            _chat_completions_url(DEEPSEEK_BASE_URL),
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=DEEPSEEK_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        return content.strip()
    except (requests.RequestException, KeyError, IndexError, ValueError) as exc:
        return fallback_summary(paper, str(exc))
