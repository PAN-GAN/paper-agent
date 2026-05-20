"""SMTP email notifier with HTML and plain-text fallback."""

from __future__ import annotations

import html
import re
import smtplib
from email.message import EmailMessage
from typing import Any

from config import (
    EMAIL_HOST,
    EMAIL_PASSWORD,
    EMAIL_PORT,
    EMAIL_TO,
    EMAIL_USE_TLS,
    EMAIL_USER,
)


def _email_configured() -> bool:
    required = [EMAIL_HOST, EMAIL_USER, EMAIL_PASSWORD, EMAIL_TO]
    return all(required)


def _authors_text(paper: dict[str, Any]) -> str:
    authors = paper.get("authors") or []
    if not authors:
        return "未知"
    visible = authors[:8]
    suffix = " 等" if len(authors) > 8 else ""
    return ", ".join(visible) + suffix


def _paper_value(paper: dict[str, Any], key: str, default: str = "未知") -> str:
    value = paper.get(key)
    return str(value) if value not in (None, "") else default


def _metric_value(value: Any, digits: int = 2) -> str:
    if value in (None, ""):
        return "未知"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _render_summary_html(body: str) -> str:
    section_pattern = re.compile(r"^(?:[一二三四五六七八九十]、|【).+")
    number_pattern = re.compile(r"^\d+[.、]\s*")
    html_parts: list[str] = []
    list_tag: str | None = None

    def close_list() -> None:
        nonlocal list_tag
        if list_tag:
            html_parts.append(f"</{list_tag}>")
            list_tag = None

    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line:
            close_list()
            continue

        escaped = html.escape(line)
        if line.startswith("【") and line.endswith("】"):
            close_list()
            continue

        if section_pattern.match(line):
            close_list()
            html_parts.append(f"<h2>{escaped}</h2>")
            continue

        if number_pattern.match(line):
            if list_tag != "ol":
                close_list()
                html_parts.append("<ol>")
                list_tag = "ol"
            item = number_pattern.sub("", line).strip()
            html_parts.append(f"<li>{html.escape(item)}</li>")
            continue

        if line.startswith(("- ", "• ")):
            if list_tag != "ul":
                close_list()
                html_parts.append("<ul>")
                list_tag = "ul"
            html_parts.append(f"<li>{html.escape(line[2:].strip())}</li>")
            continue

        close_list()
        if "：" in line and len(line.split("：", 1)[0]) <= 8:
            key, value = line.split("：", 1)
            html_parts.append(
                f'<p class="kv"><strong>{html.escape(key)}：</strong>{html.escape(value.strip())}</p>'
            )
        else:
            html_parts.append(f"<p>{escaped}</p>")

    close_list()
    return "\n".join(html_parts)


def build_email_html(title: str, body: str, paper: dict[str, Any] | None = None) -> str:
    """Build a clean newsletter-style HTML email."""

    paper = paper or {}
    metrics = paper.get("source_metrics") or {}
    paper_url = paper.get("url") or paper.get("pdf_url") or ""
    score = paper.get("score", "未评分")
    venue = paper.get("venue") or paper.get("source_type") or "未知"
    year = paper.get("publication_year") or paper.get("published_date") or "未知"
    source_type = _paper_value(paper, "source_type", "unknown")
    open_access = "是" if paper.get("is_open_access") else "未知/否"
    link_html = (
        f'<a href="{html.escape(str(paper_url))}">{html.escape(str(paper_url))}</a>'
        if paper_url
        else "无"
    )

    summary_html = _render_summary_html(body)
    safe_title = html.escape(title)
    safe_venue = html.escape(str(venue))
    safe_year = html.escape(str(year))
    safe_score = html.escape(str(score))
    safe_authors = html.escape(_authors_text(paper))
    safe_source_type = html.escape(str(source_type))
    safe_open_access = html.escape(open_access)
    safe_citations = html.escape(str(paper.get("cited_by_count") or 0))
    safe_two_year = html.escape(_metric_value(metrics.get("two_year_mean_citedness")))
    safe_h_index = html.escape(_metric_value(metrics.get("h_index"), 0))
    safe_i10_index = html.escape(_metric_value(metrics.get("i10_index"), 0))

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{safe_title}</title>
  <style>
    body {{
      margin: 0;
      padding: 0;
      background: #f4f6f8;
      color: #1f2933;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", Arial, sans-serif;
      line-height: 1.72;
    }}
    .wrap {{
      max-width: 860px;
      margin: 0 auto;
      padding: 28px 14px;
    }}
    .card {{
      background: #ffffff;
      border: 1px solid #e5e7eb;
      border-radius: 8px;
      overflow: hidden;
    }}
    .hero {{
      padding: 30px 34px 24px;
      background: #0f172a;
      color: #f8fafc;
    }}
    .eyebrow {{
      margin: 0 0 10px;
      font-size: 13px;
      letter-spacing: .04em;
      color: #93c5fd;
      text-transform: uppercase;
    }}
    h1 {{
      margin: 0;
      font-size: 25px;
      line-height: 1.35;
      font-weight: 750;
    }}
    .meta {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
      padding: 22px 34px;
      background: #f8fafc;
      border-bottom: 1px solid #e5e7eb;
    }}
    .meta-item {{
      padding: 12px 14px;
      background: #ffffff;
      border: 1px solid #e5e7eb;
      border-radius: 8px;
    }}
    .wide {{
      grid-column: 1 / -1;
    }}
    .label {{
      display: block;
      margin-bottom: 4px;
      color: #64748b;
      font-size: 12px;
    }}
    .value {{
      color: #111827;
      font-size: 14px;
      word-break: break-word;
    }}
    .content {{
      padding: 30px 34px 36px;
    }}
    h2 {{
      margin: 28px 0 12px;
      padding-top: 18px;
      border-top: 1px solid #e5e7eb;
      color: #0f172a;
      font-size: 18px;
      line-height: 1.4;
    }}
    h2:first-child {{
      margin-top: 0;
      padding-top: 0;
      border-top: 0;
    }}
    p {{
      margin: 0 0 13px;
      font-size: 15px;
    }}
    .kv strong {{
      color: #0f172a;
    }}
    ol, ul {{
      margin: 0 0 16px 22px;
      padding: 0;
    }}
    li {{
      margin: 7px 0;
      font-size: 15px;
    }}
    a {{
      color: #2563eb;
      text-decoration: none;
      word-break: break-all;
    }}
    .note {{
      margin-top: 8px;
      color: #64748b;
      font-size: 12px;
    }}
    .footer {{
      padding: 18px 34px 24px;
      color: #64748b;
      font-size: 12px;
      border-top: 1px solid #e5e7eb;
      background: #f8fafc;
    }}
    @media (max-width: 640px) {{
      .hero, .meta, .content, .footer {{
        padding-left: 20px;
        padding-right: 20px;
      }}
      .meta {{
        grid-template-columns: 1fr;
      }}
      h1 {{
        font-size: 21px;
      }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <article class="card">
      <header class="hero">
        <p class="eyebrow">Daily Research Brief</p>
        <h1>{safe_title}</h1>
      </header>
      <section class="meta">
        <div class="meta-item wide"><span class="label">作者</span><span class="value">{safe_authors}</span></div>
        <div class="meta-item"><span class="label">年份 / 来源</span><span class="value">{safe_year} · {safe_venue}</span></div>
        <div class="meta-item"><span class="label">推荐分数</span><span class="value">{safe_score}</span></div>
        <div class="meta-item"><span class="label">论文引用数</span><span class="value">{safe_citations}</span></div>
        <div class="meta-item"><span class="label">2年平均被引</span><span class="value">{safe_two_year}</span></div>
        <div class="meta-item"><span class="label">来源 h-index</span><span class="value">{safe_h_index}</span></div>
        <div class="meta-item"><span class="label">来源 i10-index</span><span class="value">{safe_i10_index}</span></div>
        <div class="meta-item"><span class="label">数据源 / 开放获取</span><span class="value">{safe_source_type} · {safe_open_access}</span></div>
        <div class="meta-item wide"><span class="label">链接</span><span class="value">{link_html}</span></div>
        <div class="wide note">注：2年平均被引来自 OpenAlex，是开放的类 IF 指标，并非 JCR 官方 Impact Factor。</div>
      </section>
      <section class="content">
        {summary_html}
      </section>
      <footer class="footer">
        由 Paper Agent 自动检索公开论文元数据并生成导读。请以原论文为准，重要结论建议回到正文核验。
      </footer>
    </article>
  </div>
</body>
</html>"""


def send_email(title: str, body: str, paper: dict[str, Any] | None = None) -> bool:
    """Send a multipart email. Returns True only after SMTP success."""

    if not _email_configured():
        print("[Email] Missing SMTP configuration. Skip email sending.")
        return False

    message = EmailMessage()
    message["Subject"] = f"【每日优秀论文推荐】{title}"
    message["From"] = EMAIL_USER
    message["To"] = EMAIL_TO
    message.set_content(body)
    message.add_alternative(build_email_html(title, body, paper), subtype="html")

    try:
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT, timeout=30) as smtp:
            if EMAIL_USE_TLS:
                smtp.starttls()
            smtp.login(EMAIL_USER, EMAIL_PASSWORD)
            smtp.send_message(message)
        print("[Email] Email sent successfully.")
        return True
    except Exception as exc:  # smtplib raises several exception families.
        print(f"[Email] Failed to send email: {exc}")
        return False
