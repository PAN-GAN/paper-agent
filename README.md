# 个人情报系统 Paper Agent

这是一个适合个人长期迭代的 Python 自动化项目：每天在 GitHub Actions 上定时检索论文，筛选一篇高质量候选，调用 DeepSeek API 生成中文解读，并通过 Email 推送给你。

系统只使用 OpenAlex 和 arXiv 的公开 API 与开放元数据，不绕过登录验证，不批量下载受版权保护的论文全文。

## 功能

- 从 OpenAlex 按关键词检索论文元数据，优先用于质量筛选。
- 从 arXiv 按关键词检索最新预印本，作为补充候选。
- 使用引用数、发表年份、关键词匹配、来源质量、开放获取状态做基础评分。
- 使用 DeepSeek OpenAI-compatible Chat Completions 生成中文论文解读。
- 使用 SMTP Email 发送纯文本推送。
- 使用 `data/sent_papers.json` 记录已推送论文，避免重复推荐。
- 使用 GitHub Actions 每天自动运行，也支持手动触发。

## 文件结构

```text
paper-agent/
├── .github/
│   └── workflows/
│       └── daily_paper.yml
├── data/
│   └── sent_papers.json
├── src/
│   ├── config.py
│   ├── fetch_openalex.py
│   ├── fetch_arxiv.py
│   ├── scorer.py
│   ├── summarizer_deepseek.py
│   ├── notifier_email.py
│   ├── notifier_telegram.py
│   ├── storage.py
│   └── main.py
├── requirements.txt
├── .env.example
└── README.md
```

## 本地运行

```bash
cd paper-agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python src/main.py
```

Windows PowerShell:

```powershell
cd paper-agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python src/main.py
```

如果没有配置 Email，程序会完成检索和总结流程，然后跳过邮件发送。为了避免误记录，只有邮件发送成功后才会写入 `data/sent_papers.json`。

## 创建 GitHub 仓库

1. 在 GitHub 新建一个空仓库，例如 `paper-agent`。
2. 将本项目内容推送到仓库根目录。
3. 打开仓库的 `Settings` -> `Actions` -> `General`。
4. 在 `Workflow permissions` 中选择 `Read and write permissions`，允许 workflow 自动提交 `data/sent_papers.json`。
5. 提交后进入 `Actions` 页面，选择 `Daily Paper Recommendation`，可以手动运行一次。

## 配置 GitHub Secrets

进入仓库 `Settings` -> `Secrets and variables` -> `Actions` -> `New repository secret`，添加以下配置。

DeepSeek 必填：

```text
DEEPSEEK_API_KEY
```

Email 推送必填：

```text
EMAIL_HOST
EMAIL_PORT
EMAIL_USER
EMAIL_PASSWORD
EMAIL_TO
EMAIL_USE_TLS
```

可选：

```text
DEEPSEEK_BASE_URL
DEEPSEEK_MODEL
DEEPSEEK_THINKING
DEEPSEEK_REASONING_EFFORT
OPENALEX_MAILTO
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
```

常见 SMTP 示例：

```text
EMAIL_HOST=smtp.qq.com
EMAIL_PORT=587
EMAIL_USER=your@qq.com
EMAIL_PASSWORD=你的邮箱授权码
EMAIL_TO=receiver@example.com
EMAIL_USE_TLS=true
```

很多邮箱不允许直接使用登录密码，需要在邮箱安全设置里创建“授权码”或“应用专用密码”。

## DeepSeek API Key

1. 登录 DeepSeek 开放平台或控制台。
2. 创建 API Key。
3. 在 GitHub Secrets 中添加 `DEEPSEEK_API_KEY`。
4. 默认模型为 `deepseek-v4-flash`。如果控制台显示的可用模型名不同，请添加或修改 `DEEPSEEK_MODEL`。
5. 默认开启思考模式：`DEEPSEEK_THINKING=enabled`，默认思考强度为 `DEEPSEEK_REASONING_EFFORT=high`。
6. 默认 `DEEPSEEK_BASE_URL` 是 `https://api.deepseek.com`。

代码使用 OpenAI-compatible Chat Completions 格式，请求路径为：

```text
https://api.deepseek.com/chat/completions
```

如果 DeepSeek 调用失败，系统会生成一份备用摘要，不会让整个任务崩溃。

推荐 DeepSeek Secrets：

```text
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_THINKING=enabled
DEEPSEEK_REASONING_EFFORT=high
```

## 修改研究领域关键词

打开 `src/config.py`，修改：

```python
KEYWORDS = [
    "artificial intelligence",
    "deep learning",
    "machine learning",
    "data science",
    "large language model",
    "graph neural network",
    "remote sensing",
]
```

建议关键词不要太多，先保持 5 到 10 个高质量方向词。关键词越宽，候选越多，但质量波动也会更明显。

## 手动运行 GitHub Actions

1. 进入仓库 `Actions` 页面。
2. 选择 `Daily Paper Recommendation`。
3. 点击 `Run workflow`。
4. 运行结束后查看日志。

如果邮件发送成功，workflow 会自动提交更新后的 `data/sent_papers.json`。

## 修改每天推送时间

GitHub Actions 的 cron 使用 UTC 时间，不是北京时间。

当前配置：

```yaml
- cron: "0 0 * * *"
```

含义是 UTC 每天 00:00，也就是北京时间每天 08:00。

如果你想北京时间每天 09:30 推送，需要换算为 UTC 01:30：

```yaml
- cron: "30 1 * * *"
```

## Telegram Bot

当前项目默认主推送渠道是 Email，`src/notifier_telegram.py` 已保留轻量实现，后续可以在 `main.py` 中接入。

创建 Telegram Bot：

1. 在 Telegram 搜索 `@BotFather`。
2. 发送 `/newbot`。
3. 按提示创建 bot，获得 `TELEGRAM_BOT_TOKEN`。
4. 给你的 bot 发送一条消息。
5. 访问下面地址获取 chat id：

```text
https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/getUpdates
```

返回 JSON 中的 `message.chat.id` 就是 `TELEGRAM_CHAT_ID`。

## 常见问题

### 为什么没有推送？

常见原因：

- 没有配置 Email Secrets。
- SMTP 密码不是授权码。
- GitHub Actions 没有网络访问目标 SMTP 服务。
- 没有检索到未推送论文。
- 邮件发送失败时，系统不会写入去重记录。

请先查看 Actions 日志中的 `[Email]`、`[Main]`、`[OpenAlex]`、`[arXiv]` 输出。

### 为什么论文质量不稳定？

当前评分是简单启发式，适合个人学习和快速迭代。OpenAlex 的引用数对经典论文更友好，arXiv 对新论文更友好但噪声更大。

你可以在 `src/scorer.py` 中调整：

- `HIGH_QUALITY_VENUES`
- 引用数权重
- 年份新鲜度权重
- 关键词匹配权重
- `MIN_SCORE`

### 为什么 DeepSeek 调用失败？

常见原因：

- `DEEPSEEK_API_KEY` 未配置或填错。
- 账户余额不足。
- `DEEPSEEK_MODEL` 与控制台实际模型名不一致。
- API 服务临时不可用。
- `DEEPSEEK_BASE_URL` 配置错误。

调用失败时，系统会返回备用摘要，保证任务不中断。

### GitHub Actions 时间为什么和北京时间不同？

GitHub Actions cron 固定使用 UTC。北京时间是 UTC+8。

例如：

- 北京时间 08:00 = UTC 00:00
- 北京时间 12:00 = UTC 04:00
- 北京时间 20:30 = UTC 12:30

### 如何避免重复推送？

系统使用 `data/sent_papers.json` 记录已经推送成功的论文：

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

GitHub Actions 成功发送邮件后，会自动提交这个文件。请确认仓库 Actions 权限允许写入，否则每次运行都会回到旧记录。

## 后续可迭代方向

- 接入钉钉机器人 Webhook。
- 将评分细节一起写入邮件。
- 增加关键词分组，例如 LLM、遥感、图神经网络分别推送。
- 增加“最近 7 天论文”过滤。
- 接入 Notion、飞书或数据库保存长期阅读记录。
