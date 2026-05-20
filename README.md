# 个人科研情报系统 Paper Agent

这是一个部署在 GitHub Actions 上的每日论文推荐 Agent。它会每天自动检索论文、筛选高质量候选、调用 DeepSeek 生成中文导读，并通过 QQ 邮箱或其他 SMTP 邮箱发送给你。

系统只使用公开 API 和开放元数据，不绕过登录验证，不批量下载受版权保护的论文全文。

## 功能

- 多源检索：OpenAlex、Semantic Scholar、arXiv、OpenReview。
- 元数据增强：Crossref、Unpaywall、Semantic Scholar。
- 自动评分：引用数、发表年份、关键词相关性、来源质量、开放获取、影响力引用、开放指标。
- 中文导读：DeepSeek OpenAI-compatible Chat Completions。
- 邮件推送：SMTP Email，支持 QQ 邮箱。
- 去重记录：`data/sent_papers.json`。
- 定时运行：GitHub Actions，每天自动运行，也支持手动触发。

## 文件结构

```text
paper-agent/
├── .github/workflows/daily_paper.yml
├── data/sent_papers.json
├── src/
│   ├── config.py
│   ├── fetch_openalex.py
│   ├── fetch_semantic_scholar.py
│   ├── fetch_arxiv.py
│   ├── fetch_openreview.py
│   ├── enrichers.py
│   ├── paper_merge.py
│   ├── scorer.py
│   ├── summarizer_deepseek.py
│   ├── notifier_email.py
│   ├── storage.py
│   └── main.py
├── requirements.txt
├── .env.example
└── README.md
```

## 快速开始

推荐使用方式是 Fork 本仓库，然后在自己的 GitHub 仓库里配置 Secrets。

1. 打开本仓库页面。
2. 点击右上角 `Fork`。
3. 进入你自己的 fork 仓库。
4. 按下面步骤配置 GitHub Actions 权限和 Secrets。
5. 手动运行一次 workflow，确认能收到邮件。

Fork 后，你的仓库不会拿到原作者的 API Key、邮箱密码或任何 Secrets。你必须配置自己的密钥和邮箱授权码。

## 第一步：开启 GitHub Actions 写权限

这个项目会在邮件发送成功后更新 `data/sent_papers.json`，用于避免重复推送。所以需要允许 GitHub Actions 写入仓库。

在你的 fork 仓库中进入：

```text
Settings -> Actions -> General
```

找到 `Workflow permissions`，选择：

```text
Read and write permissions
```

然后保存。

如果没有开启这个权限，邮件可能能发出去，但去重记录无法自动提交，后续可能重复推送同一篇论文。

## 第二步：配置 GitHub Secrets

进入：

```text
Settings -> Secrets and variables -> Actions -> Secrets -> New repository secret
```

每个配置都要单独新建一次。页面里有两个输入框：

```text
Name   = 配置名
Secret = 配置值
```

不要把多个配置写在同一个 Secret 里。

### 必填：DeepSeek

```text
Name: DEEPSEEK_API_KEY
Secret: 你的 DeepSeek API Key
```

推荐再添加：

```text
Name: DEEPSEEK_BASE_URL
Secret: https://api.deepseek.com
```

```text
Name: DEEPSEEK_MODEL
Secret: deepseek-v4-flash
```

```text
Name: DEEPSEEK_THINKING
Secret: enabled
```

```text
Name: DEEPSEEK_REASONING_EFFORT
Secret: high
```

如果 DeepSeek 控制台里的模型名发生变化，只需要修改 `DEEPSEEK_MODEL`。

### 必填：QQ 邮箱 / SMTP 邮件

如果你用 QQ 邮箱，按下面配置：

```text
Name: EMAIL_HOST
Secret: smtp.qq.com
```

```text
Name: EMAIL_PORT
Secret: 587
```

```text
Name: EMAIL_USER
Secret: 你的 QQ 邮箱，例如 123456@qq.com
```

```text
Name: EMAIL_PASSWORD
Secret: QQ 邮箱授权码，不是 QQ 登录密码
```

```text
Name: EMAIL_TO
Secret: 接收论文推送的邮箱，例如 123456@qq.com
```

```text
Name: EMAIL_USE_TLS
Secret: true
```

`EMAIL_USER` 是发件人，`EMAIL_TO` 是收件人。

如果两者填同一个邮箱，就是自己发给自己，这很常见，也最简单。

### QQ 邮箱授权码是什么

`EMAIL_PASSWORD` 不要填 QQ 登录密码，要填 QQ 邮箱的 SMTP 授权码。

大致路径是：

```text
QQ邮箱 -> 设置 -> 账号 -> POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务
```

开启 SMTP 服务后，QQ 邮箱会生成一个授权码。把这个授权码填到：

```text
EMAIL_PASSWORD
```

如果 SMTP 登录失败，最常见原因就是这里填成了 QQ 登录密码。

### 可选：免费论文数据源

这些不是必填，不填也能运行。

```text
Name: OPENALEX_MAILTO
Secret: 你的邮箱
```

`OPENALEX_MAILTO` 是给 OpenAlex 的联系邮箱，只是礼貌标识，不是邮箱密码，也不会用来发邮件。

```text
Name: UNPAYWALL_EMAIL
Secret: 你的邮箱
```

`UNPAYWALL_EMAIL` 用于 Unpaywall 查询合法开放获取版本。如果不填，会复用 `OPENALEX_MAILTO`。

```text
Name: SEMANTIC_SCHOLAR_API_KEY
Secret: 你的 Semantic Scholar 免费 API Key
```

`SEMANTIC_SCHOLAR_API_KEY` 可选，但建议申请免费 key，稳定性更好。

## 第三步：修改研究方向

打开 `src/config.py`，修改 `KEYWORDS`。

例如你关注大模型和遥感：

```python
KEYWORDS = [
    "large language model",
    "retrieval augmented generation",
    "AI agent",
    "remote sensing",
    "satellite image",
    "change detection",
]
```

建议保持 3 到 8 个关键词。关键词越宽，候选越多，但质量波动也会更明显。

## 第四步：手动运行一次

进入：

```text
Actions -> Daily Paper Recommendation -> Run workflow
```

运行结束后点开日志，重点看：

```text
[Email] Email sent successfully.
[Main] Paper marked as sent.
```

如果看到这两行，并且邮箱收到了邮件，就说明系统已经跑通。

## 第五步：每天自动推送

默认 workflow 配置是：

```yaml
- cron: "0 0 * * *"
```

GitHub Actions 使用 UTC 时间。北京时间是 UTC+8。

所以：

```text
UTC 00:00 = 北京时间 08:00
```

如果你想改成北京时间每天 09:30，需要写成：

```yaml
- cron: "30 1 * * *"
```

## 邮件是谁发出的

邮件发件人就是 `EMAIL_USER`。

例如：

```text
EMAIL_USER=123456@qq.com
EMAIL_PASSWORD=QQ邮箱授权码
EMAIL_TO=receiver@example.com
```

系统会登录 `123456@qq.com` 的 SMTP 服务，然后从这个邮箱发论文推荐到 `receiver@example.com`。

代码里对应逻辑在 `src/notifier_email.py`：

```python
message["From"] = EMAIL_USER
message["To"] = EMAIL_TO
smtp.login(EMAIL_USER, EMAIL_PASSWORD)
```

## 免费数据源说明

当前版本使用：

```text
OpenAlex + Semantic Scholar + arXiv + Unpaywall + Crossref + OpenReview
```

说明：

- OpenAlex：免费，主数据源，提供论文和来源指标。
- Semantic Scholar：免费，补充引用数、影响力引用、相关元数据。
- arXiv：免费，补充最新预印本。
- OpenReview：免费，补充 AI 顶会/评审平台论文。
- Crossref：免费，补 DOI、出版商、期刊等元数据。
- Unpaywall：免费，查合法开放获取版本和 OA PDF。

系统不会使用 Sci-Hub，不绕过数据库登录，不自动下载受版权保护的全文。

## 本地运行

```bash
cd paper-agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python src/main.py
```

Windows PowerShell：

```powershell
cd paper-agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python src/main.py
```

## 常见问题

### 为什么没有收到邮件

常见原因：

- GitHub Secrets 没填完整。
- `EMAIL_PASSWORD` 填成了 QQ 登录密码，而不是邮箱授权码。
- `EMAIL_HOST` 或 `EMAIL_PORT` 写错。
- DeepSeek API Key 无效或余额不足。
- 没有检索到未推送论文。
- 邮件发送失败时，系统不会写入去重记录。

先看 Actions 日志中的：

```text
[Main]
[Email]
[OpenAlex]
[Semantic Scholar]
[arXiv]
[OpenReview]
```

### 为什么论文质量不稳定

论文推荐是启发式评分，不是人工审稿。当前评分综合：

- 关键词匹配
- 论文引用数
- Semantic Scholar 影响力引用
- OpenAlex 来源指标
- 年份新鲜度
- 来源/会议/期刊质量
- 是否开放获取
- 是否有合法开放 PDF

如果方向太宽，推荐会更发散。建议先把 `KEYWORDS` 收窄到你真正关心的领域。

### 如何避免重复推送

系统使用 `data/sent_papers.json` 记录已推送论文：

```json
[
  {
    "paper_id": "...",
    "title": "...",
    "url": "...",
    "sent_at": "..."
  }
]
```

邮件发送成功后，GitHub Actions 会自动提交这个文件。请确认 Actions 权限是 `Read and write permissions`。

### 分享给别人会泄露我的 API Key 吗

不会。

GitHub Secrets 不会被别人看到，Fork 仓库也不会复制你的 Secrets。别人要使用这个项目，必须配置自己的 DeepSeek API Key 和邮箱授权码。

### OpenAlex Mailto 是什么

`OPENALEX_MAILTO` 是给 OpenAlex 的联系邮箱，用来礼貌标识 API 请求来源。

它不是邮箱密码，也不会用于发邮件。不填也能运行，但建议填自己的邮箱。
