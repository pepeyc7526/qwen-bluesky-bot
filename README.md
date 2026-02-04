[![GitHub Actions](https://img.shields.io/github/actions/workflow/status/pepeyc7526/qwen-bluesky-bot/bluesky-bot.yml?style=flat&logo=github)](https://github.com/pepeyc7526/qwen-bluesky-bot/actions)
[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)](https://python.org)
[![LLM](https://img.shields.io/badge/Qwen2--7B-GGUF-8A2BE2)](https://huggingface.co/Qwen/Qwen2-7B-Instruct)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Bluesky](https://img.shields.io/badge/Bluesky-%23F3F9FF?logo=image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZmlsbD0iIzYzNjdGRiIgZD0iTTEyIDIuNjY3YTkuMzMzIDkuMzMzIDAgMDE5LjMzMyA5LjMzMyA5LjMzMyA5LjMzMyAwIDAxLTkuMzMzIDkuMzMzIDkuMzMzIDkuMzMzIDAgMDEtOS4zMzMtOS4zMzMgOS4zMzMgOS4zMzMgMCAwMTkuMzMzLTkuMzMzem0wIDEuNjY2QTcuNjY3IDcuNjY3IDAgMTE0LjY2NyAxMiA3LjY2NyA3LjY2NyAwIDExMTIgNC42NjdabTAgMTQuNjY2QTcuNjY3IDcuNjY3IDAgMTE5LjMzMyAxMiA3LjY2NyA3LjY2NyAwIDExMTIgMTkuMzMzWiIvPjwvc3ZnPg==)](https://bsky.app)

# 🤖 Qwen Bluesky Bot

A **private, self-hosted AI assistant** for your Bluesky account — powered by the open-source **Qwen2-7B** model.  
Runs entirely on free infrastructure. No external APIs. Full user control.

> 🔒 **All state is stored in encrypted GitHub Secrets — never committed to the repo. Your history stays private.**

---

## ✨ Features

- **100% private**: State (last processed time, reply history) stored in **GitHub Secrets**, not in public files
- **Free & open**: Runs on GitHub Actions with quantized **Qwen2-7B GGUF (Q4_K_M)**
- **Smart replies**: Only responds to:
  - Direct mentions: `@your-bot.bsky.social hello`
  - Replies to its own posts
- **No spam**: Ignores unrelated threads
- **Duplicate protection**: Remembers last **100 responses** to avoid repeats
- ⏳ **Natural pacing**: Random 1–2 minute delays between replies
- 🔍 **Live web search**: Type `'web' <query>` to fetch real-time answers
- 💾 **Persistent memory**: State auto-saved via encrypted GitHub Secrets API

---

## 🚀 Quick Start

### 1. Fork this repository

### 2. Add secrets in  
`Settings → Secrets and variables → Actions`

| Secret | Value |
|--------|-------|
| `BOT_HANDLE` | Your bot’s handle (e.g. `bot.yourname.bsky.social`) |
| `BOT_PASSWORD` | [App password](https://bsky.app/settings/app-passwords) from Bluesky |
| `BOT_DID` | Run `atproto identity resolve <handle>` to get it |
| `OWNER_DID` | Your personal account’s DID |
| `PAT` | GitHub Personal Access Token (**classic**, `repo` scope) |
| `BOT_STATE` | Initial state (see below) |

> 💡 **Initial `BOT_STATE`**:  
> ```json
> {
>   "last_processed": "2026-01-01T00:00:00.000Z",
>   "recent_replies": [],
>   "search_usage": {"count": 0, "month": 1}
> }
> ```
> Replace the date with your last notification timestamp to avoid processing old messages.

### 3. Enable Actions & run manually

Go to **Actions → Bluesky AI Bot → Run workflow**

---

## 🔍 Web Search

To trigger a live search, use **single quotes** around `web`:

**@your-bot.bsky.social 'web' weather in Tokyo?**


✅ Works: `'web' climate change`  
❌ Ignored: `web climate change` (no quotes)

> ⚠️ DuckDuckGo API is used — no keys needed. Results are factual summaries (not future predictions).

---

## ⚡ Instant Control: Use the Browser Extension

Scheduled runs are **disabled by default** to give you full control.

👉 **Install the official extension**:  
[**qwen-bluesky-bot-extension**](https://github.com/pepeyc7526/qwen-bluesky-bot-extension)

- One-click trigger from your browser
- Secure: uses your PAT locally
- No waiting — instant `workflow_dispatch`

> 💡 You can still enable cron in `.github/workflows/bluesky-bot.yml` if preferred.

---

## 🛠️ Tech Stack

- **Model**: Qwen2-7B-Instruct-GGUF (Q4_K_M)
- **Runtime**: Python 3.11 + `llama-cpp-python`
- **Host**: GitHub Actions (free tier, CPU-only)
- **Search**: DuckDuckGo Instant Answer API (no key required)
- **State**: Encrypted GitHub Secrets (via `pynacl`)

---

> “AI should accelerate progress — not create barriers.”  
> This bot is built for **privacy**, **efficiency**, and **user sovereignty**.

---

Made with ❤️ using **[Qwen AI](https://chat.qwen.ai/)** and **[Bluesky](https://bsky.app/)**.
