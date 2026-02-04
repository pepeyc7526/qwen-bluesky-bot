[![GitHub Actions](https://img.shields.io/github/actions/workflow/status/pepeyc7526/qwen-bluesky-bot/bluesky-bot.yml?style=flat&logo=github)](https://github.com/pepeyc7526/qwen-bluesky-bot/actions)
[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)](https://python.org)
[![LLM](https://img.shields.io/badge/Qwen2--7B-GGUF-8A2BE2)](https://huggingface.co/Qwen/Qwen2-7B-Instruct)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Bluesky](https://img.shields.io/badge/Bluesky-%23F3F9FF?logo=image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZmlsbD0iIzYzNjdGRiIgZD0iTTEyIDIuNjY3YTkuMzMzIDkuMzMzIDAgMDE5LjMzMyA5LjMzMyA5LjMzMyA5LjMzMyAwIDAxLTkuMzMzIDkuMzMzIDkuMzMzIDkuMzMzIDAgMDEtOS4zMzMtOS4zMzMgOS4zMzMgOS4zMzMgMCAwMTkuMzMzLTkuMzMzem0wIDEuNjY2QTcuNjY3IDcuNjY3IDAgMTE0LjY2NyAxMiA3LjY2NyA3LjY2NyAwIDExMTIgNC42NjdabTAgMTQuNjY2QTcuNjY3IDcuNjY3IDAgMTE5LjMzMyAxMiA3LjY2NyA3LjY2NyAwIDExMTIgMTkuMzMzWiIvPjwvc3ZnPg==)](https://bsky.app)

# 🤖 Qwen Bluesky Bot

A **private, self-hosted AI assistant** for your Bluesky account — powered by the open-source **Qwen2-7B** model.  
Runs entirely on free infrastructure. No external APIs. Full user control.

> ✨ **Now with smart reply filtering & duplicate prevention!**

---

## ✅ Features

- **Private & local**: All inference runs on GitHub Actions via `llama-cpp-python`
- **Free forever**: Uses quantized **Qwen2-7B GGUF (Q4_K_M)** — no paid services
- **Smart replies**: Only responds to:
  - Direct mentions: `@your-bot.bsky.social hello`
  - Replies to its own posts (no mention needed)
- **No spam**: Ignores replies in threads not addressed to it
- **Duplicate protection**: Remembers last **100 responses** to avoid repeats
- ⏳ **Natural pacing**: Random 1–2 minute delays between replies
- 🔍 **Web search** (optional): Type `web <query>` to fetch live results
- 📅 **Monthly quota**: Web search counter resets automatically
- 💾 **Persistent memory**: Saves state via Git-committed JSON files

---

## 🚀 Quick Start

1. **Fork this repo**
2. Add these **secrets** in  
   `Settings → Secrets and variables → Actions`:

| Secret | Value |
|--------|-------|
| `BOT_HANDLE` | Your bot’s handle (e.g. `bot.yourname.bsky.social`) |
| `BOT_PASSWORD` | [App password](https://bsky.app/settings/app-passwords) from Bluesky |
| `BOT_DID` | Run `atproto identity resolve <handle>` to get it |
| `OWNER_DID` | Your personal account’s DID |
| `PAT` | GitHub Personal Access Token (**classic**, `repo` scope) |

> 🔑 Optional: Add `GOOGLE_API_KEY` + `GOOGLE_CSE_ID` for web search

3. **Enable Actions** and run the workflow manually

> 📝 On first run, the bot auto-creates `last_processed.json` and `search_usage.json`.

---

## ⚡ Instant Control: Use the Browser Extension!

Scheduled runs are **disabled by default** (no cron) to give you full control and avoid GitHub’s 20-minute limit.

👉 **Install the official extension**:  
[**qwen-bluesky-bot-extension**](https://github.com/pepeyc7526/qwen-bluesky-bot-extension)

- One-click trigger from your browser toolbar
- No waiting — instant runs via `workflow_dispatch`
- Secure: your PAT stays in your browser

> 💡 You can still enable hourly cron if you prefer — just uncomment the schedule block in `.github/workflows/bluesky-bot.yml`.

---

## 🛠️ Tech Stack

- **Model**: Qwen2-7B-Instruct-GGUF (Q4_K_M)
- **Runtime**: Python 3.11 + `llama-cpp-python`
- **Host**: GitHub Actions (free tier, CPU-only)
- **Protocol**: Bluesky AT Protocol (HTTP)

---

> “AI should accelerate progress — not create barriers.”  
> This bot is built for **privacy**, **efficiency**, and **user sovereignty**.

---

Made with ❤️ using **[Qwen AI](https://chat.qwen.ai/)** and **[Bluesky](https://bsky.app/)**.
