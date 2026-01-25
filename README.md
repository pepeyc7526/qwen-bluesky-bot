[![GitHub Actions](https://img.shields.io/github/actions/workflow/status/pepeyc7526/qwen-bluesky-bot/bluesky-bot.yml?style=flat&logo=github)](https://github.com/pepeyc7526/qwen-bluesky-bot/actions)
[![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)](https://python.org)
[![LLM](https://img.shields.io/badge/Qwen2--7B-GGUF-8A2BE2)](https://huggingface.co/Qwen/Qwen2-7B-Instruct)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Bluesky](https://img.shields.io/badge/Bluesky-%23F3F9FF?logo=image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZmlsbD0iIzYzNjdGRiIgZD0iTTEyIDIuNjY3YTkuMzMzIDkuMzMzIDAgMDE5LjMzMyA5LjMzMyA5LjMzMyA5LjMzMyAwIDAxLTkuMzMzIDkuMzMzIDkuMzMzIDkuMzMzIDAgMDEtOS4zMzMtOS4zMzMgOS4zMzMgOS4zMzMgMCAwMTkuMzMzLTkuMzMzem0wIDEuNjY2QTcuNjY3IDcuNjY3IDAgMTE0LjY2NyAxMiA3LjY2NyA3LjY2NyAwIDExMTIgNC42NjdabTAgMTQuNjY2QTcuNjY3IDcuNjY3IDAgMTE5LjMzMyAxMiA3LjY2NyA3LjY2NyAwIDExMTIgMTkuMzMzWiIvPjwvc3ZnPg==)](https://bsky.app)

# 🤖 Qwen2 Bluesky AI Bot

A private, self-hosted AI assistant for **Bluesky** powered by the open-source **Qwen2-7B** model.  
Runs entirely on free infrastructure. No external APIs. Full user control.

---

## ✨ Features

- 🔒 **Private & local**: All inference happens on GitHub Actions using `llama-cpp-python`
- 💸 **Free**: Uses quantized **Qwen2-7B GGUF (Q4_K_M)** — no paid services
- 🧠 **Context-aware**: Understands replies to its own posts
- ⏳ **Natural pacing**: Random 1–2 minute delays between replies (avoids spam detection)
- 🌐 **Web search**: Type `web <query>` to fetch live results (optional)
- 📅 **Monthly quota**: Web search usage resets automatically each month
- 🧠 **Persistent memory**: Remembers last processed notification via Git-committed state

---

## 💬 How to Use

The bot only responds to **its owner** (verified by DID). You can:

- **Mention it**:  
  `@your-bot.bsky.social what is fusion?`

- **Reply directly** to its post (no mention needed):  
  Just write `explain more`

- **Trigger web search**:  
  `@your-bot.bsky.social web what is chainbase.com?`

> ⚠️ Web search requires valid `GOOGLE_API_KEY` and `GOOGLE_CSE_ID` in secrets.

---

## ✨ Features
- **Customizable personality** via system prompt  
  *(official, humorous, analytical, or ultra-minimalist)*
- **State persistence** between runs using JSON files
- **Smart reply threading** (handles nested conversations)
- **Rate-limited posting** (60-120s delays to avoid spam)
- **Automatic monthly usage tracking**
- **Zero external dependencies** (runs on CPU-only machines)

---

## 🛠️ Quick Setup
1. Fork this repo
2. Add secrets: `BOT_HANDLE`, `BOT_PASSWORD`, `BOT_DID`, `OWNER_DID`
3. Place your `qwen2-7b-instruct-q4_k_m.gguf` in `/models`
4. Enable GitHub Actions

---

## ⚙️ Setup

1. **Fork this repository**
2. Add these **secrets** in `Settings → Secrets and variables → Actions`:
   - `BOT_HANDLE` — your bot’s Bluesky handle (e.g. `bot-example.bsky.social`)
   - `BOT_PASSWORD` — app password (create in Bluesky settings → App passwords)
   - `BOT_DID` — your bot’s DID (`atproto identity resolve <handle>`)
   - `OWNER_DID` — your personal account’s DID
   - `PAT` — GitHub Personal Access Token with `repo` scope (for committing state)
   - *(Optional)* `GO GOOGLE_API_KEY` & `GOOGLE_CSE_ID` — for web search

3. **Enable Actions** and run the workflow manually

> 💡 On first run, the bot auto-creates `last_processed.json` and `search_usage.json`.

---

🎮 One-Click Manual Runs (Browser Extension)

By default, scheduled runs are disabled to give you full control and avoid hitting GitHub Actions limits.

🔧 Current setup
In .github/workflows/bluesky-bot.yml, the cron schedule is commented out:

on:

    # schedule:
    #   - cron: '0 * * * *'
  
  workflow_dispatch:

This means the bot only runs when you trigger it manually.

🚀 Option 1: Use the Browser Extension (Recommended)
Install the official extension: https://github.com/pepeyc7526/qwen-bluesky-bot-extension
Click its icon → "Run Bluesky Bot"
Done! No cron, no limits, instant runs.

💡 Why? GitHub Actions has a hard limit of once every 20 minutes for scheduled workflows. The extension bypasses this by using manual triggers (workflow_dispatch), giving you true on-demand control.

⏱️ Option 2: Enable Automatic Hourly Runs
If you prefer automatic runs (once per hour):
Open .github/workflows/bluesky-bot.yml
Uncomment these lines:

    # schedule:
    #   - cron: '0 * * * *'

→ becomes:

    schedule:
      - cron: '0 * * * *'

Commit the change

⚠️ Note: Even with cron enabled, you can still use the extension for instant runs between scheduled intervals.

---

## 📦 Tech Stack

- **Model**: [Qwen2-7B-Instruct-GGUF (Q4_K_M)](https://huggingface.co/Qwen/Qwen2-7B-Instruct-GGUF)
- **Runtime**: Python 3.11 + `llama-cpp-python`
- **Host**: GitHub Actions (free tier)
- **Protocol**: Bluesky AT Protocol (via HTTP)

---

## 🚫 Limitations

- Bluesky API does not support real-time notification streams
- State persistence relies on Git commits (due to serverless execution)
- Web search is rate-limited (~100 queries/month)

---

## 🌱 Philosophy

> “AI should accelerate progress — not create barriers.”  
> This bot is built for **privacy**, **efficiency**, and **user sovereignty**.

---

## 📜 License

MIT License

Permission is hereby granted, free of charge, to any person obtaining a copy  
of this software and associated documentation files, to deal in the Software  
without restriction, including without limitation the rights to use, copy,  
modify, merge, publish, distribute, sublicense, and/or sell copies of the  
Software, and to permit persons to whom the Software is furnished to do so,  
subject to the above copyright notice and this permission notice.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.

---

Made with ❤️ using **[Qwen AI](https://chat.qwen.ai/)** and **[Bluesky](https://bsky.app/)**.
