"""Generate a richer Chinese paper interpretation with DeepSeek."""

from __future__ import annotations

from typing import Any

import requests

from config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
    DEEPSEEK_REASONING_EFFORT,
    DEEPSEEK_THINKING,
    DEEPSEEK_TIMEOUT_SECONDS,
    KEYWORDS,
)


def _chat_completions_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    return f"{base}/chat/completions"


def _authors_text(paper: dict[str, Any], limit: int = 8) -> str:
    authors = paper.get("authors") or []
    if not authors:
        return "未知"
    visible = authors[:limit]
    suffix = " 等" if len(authors) > limit else ""
    return ", ".join(visible) + suffix


def _source_metrics_text(paper: dict[str, Any]) -> str:
    metrics = paper.get("source_metrics") or {}
    semantic = paper.get("semantic_scholar") or {}
    unpaywall = paper.get("unpaywall") or {}
    values = [
        f"候选来源：{', '.join(paper.get('source_types') or [paper.get('source_type', 'unknown')])}",
        f"论文引用数：{paper.get('cited_by_count', 0)}",
        f"影响力引用：{paper.get('influential_citation_count') or semantic.get('influential_citation_count') or 0}",
        f"OpenAlex 2年平均被引：{metrics.get('two_year_mean_citedness', '未知')}",
        f"来源 h-index：{metrics.get('h_index', '未知')}",
        f"来源 i10-index：{metrics.get('i10_index', '未知')}",
        f"来源总被引：{metrics.get('source_cited_by_count', '未知')}",
        f"合法开放PDF：{paper.get('oa_pdf_url') or paper.get('pdf_url') or unpaywall.get('best_oa_pdf_url') or '未知'}",
    ]
    return "；".join(values)


def fallback_summary(paper: dict[str, Any], reason: str | None = None) -> str:
    """Return a useful local summary when the model call is unavailable."""

    reason_text = f"\n\n说明：DeepSeek 调用失败，已生成备用导读。原因：{reason}" if reason else ""
    abstract = paper.get("abstract") or "暂无摘要。"
    return f"""【今日优秀论文推荐】

标题：{paper.get("title", "未知")}
作者：{_authors_text(paper)}
年份：{paper.get("publication_year") or paper.get("published_date") or "未知"}
来源：{paper.get("venue") or paper.get("source_type") or "未知"}
链接：{paper.get("url") or paper.get("pdf_url") or "无"}

推荐指数：{paper.get("score", "未评分")}
开放指标：{_source_metrics_text(paper)}
适合方向：{", ".join(KEYWORDS[:5])}

一、这篇论文在解决什么问题
{abstract}

二、方法和思路概览
从当前元数据看，这篇论文值得先围绕研究问题、方法设计、实验验证和可复现性四个角度阅读。建议把摘要中的任务定义、数据来源、评价指标和主要结论标出来。

三、核心看点
1. 关注作者如何界定问题，以及这个问题为什么重要。
2. 关注方法是否比已有方案更简单、更有效或更可解释。
3. 关注实验设计是否覆盖了关键对比、消融和失败案例。
4. 如果有开放代码或数据，可进一步判断复现成本。

四、为什么值得读
这篇论文与当前关注的 AI、数据科学或深度学习方向相关，可用于跟踪研究趋势、积累选题意识，并帮助你建立对该方向常见方法和评价方式的判断。

五、阅读难度与复现难度
阅读难度：中级
复现难度：中

六、建议阅读路线
1. 先读标题、摘要和引言，确认研究问题是否与你的方向相关。
2. 再看方法图、算法流程或模型结构，抓住核心假设。
3. 接着看实验设置、基线、指标和消融结果。
4. 最后看局限性、代码链接和后续可扩展方向。{reason_text}
"""


def summarize_paper(paper: dict[str, Any]) -> str:
    """Call DeepSeek with OpenAI-compatible Chat Completions format."""

    if not DEEPSEEK_API_KEY:
        return fallback_summary(paper, "DEEPSEEK_API_KEY is not configured")

    prompt = f"""
请用中文为下面这篇论文写一份“可直接邮件推送”的深度导读，面向 AI、数据科学、深度学习学习者和研究入门者。

论文信息：
标题：{paper.get("title")}
作者：{_authors_text(paper)}
年份：{paper.get("publication_year") or paper.get("published_date")}
来源：{paper.get("venue") or paper.get("source_type")}
链接：{paper.get("url") or paper.get("pdf_url")}
推荐分数：{paper.get("score")}
开放指标：{_source_metrics_text(paper)}
关键词：{paper.get("matched_keyword")}
摘要：{paper.get("abstract")}

写作要求：
- 内容要比普通摘要更丰富，像一封研究 newsletter。
- 不要编造论文摘要里没有的实验细节、数据集名称、指标或结论；如果信息不足，请明确说“摘要中未说明”。
- 语言通俗但准确，避免营销化夸张。
- 每段尽量短，方便在手机邮件里阅读。
- 不要使用 Markdown 表格。

请严格按下面结构输出：

【今日优秀论文推荐】

标题：
作者：
年份：
来源：
链接：

推荐指数：
开放指标：
说明候选来源、论文引用数、Semantic Scholar 影响力引用、OpenAlex 2年平均被引、来源 h-index / i10-index、合法开放 PDF。注意：OpenAlex 2年平均被引是开放的类 IF 指标，不要称为官方 JCR Impact Factor。
适合方向：
一句话结论：

一、这篇论文在解决什么问题
用 2-3 段说明研究背景、核心问题和它为什么重要。

二、方法和思路概览
用 2-4 段解释论文大致怎么做。不要堆术语，要解释关键机制、输入输出、建模思路或算法流程。

三、核心贡献与创新点
1.
2.
3.
必要时可以写第 4 点。

四、实验与证据怎么看
说明应该重点看哪些实验、对比、消融或评价指标。如果摘要没有实验信息，请明确说明摘要中未说明，并告诉读者应去论文正文确认什么。

五、对学习和研究的价值
说明这篇论文对 AI / 数据科学 / 深度学习学习者有什么启发，适合用来学习什么能力。

六、可能的局限与阅读提醒
列出 2-3 个读者需要警惕或进一步确认的地方。

七、阅读难度与复现难度
阅读难度：初级 / 中级 / 较难 / 很难，并用一句话解释。
复现难度：低 / 中 / 高，并用一句话解释。

八、建议阅读路线
1.
2.
3.
4.

九、延伸关键词
给出 5-8 个中英文混合关键词，方便后续检索。
""".strip()

    payload: dict[str, Any] = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "你是一名严谨的中文科研论文导读作者，擅长把论文写成清晰、克制、有学习价值的邮件简报。",
            },
            {"role": "user", "content": prompt},
        ],
    }
    if DEEPSEEK_THINKING == "enabled":
        payload["thinking"] = {"type": "enabled"}
        if DEEPSEEK_REASONING_EFFORT in {"high", "max"}:
            payload["reasoning_effort"] = DEEPSEEK_REASONING_EFFORT
    else:
        payload["thinking"] = {"type": "disabled"}
        payload["temperature"] = 0.3

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
