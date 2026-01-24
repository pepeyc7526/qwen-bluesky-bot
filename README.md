# 🤖 Qwen2 Bluesky AI Bot

A private, self-hosted AI assistant for [Bluesky](https://bsky.app) that runs **100% locally** using the **Qwen2-7B** model.  
No external APIs. No data leaks. Fully under your control.

---

## ✨ Features

- ✅ **Private & local**: Runs on GitHub Actions with **no cloud costs**
- ✅ **Free**: Uses open-source **Qwen2-7B GGUF** (4-bit quantized)
- ✅ **Context-aware**: Understands replies to its own posts
- ✅ **Natural behavior**: Random 1–2 min delays between replies (avoids spam detection)
- ✅ **Web search** (optional): Integrates Google Custom Search (with quota limits)
- ✅ **Persistent memory**: Remembers last processed notification via `last_processed.json`

---

## 🔐 How It Works

- The bot **only responds to you** (verified by your DID: `did:plc:topho472iindqxv5hm7nzww2`)
- Supports both:
  - **Mentions**: `@your-bot.bsky.social what is fusion?`
  - **Replies**: Just reply to the bot’s post — no mention needed
- All state is saved between runs via Git commits (`last_processed.json`, `search_usage.json`)

> 💬 **Tip**: To continue a conversation, always reply directly to the bot’s post or mention it.

---

## ⚙️ Setup

1. **Fork this repo**
2. Add these **secrets** in `Settings → Secrets and variables → Actions`:
   - `BOT_HANDLE` — your bot’s Bluesky handle (e.g. `bot-pepeyc7526.bsky.social`)
   - `BOT_PASSWORD` — app password (generate in Bluesky settings)
   - `BOT_DID` — your bot’s DID (find via `atproto identity resolve`)
   - `OWNER_DID` — your personal DID (`did:plc:topho472iindqxv5hm7nzww2`)
   - `PAT` — GitHub Personal Access Token with `repo` scope (for committing state)
   - *(Optional)* `GOOGLE_API_KEY` & `GOOGLE_CSE_ID` for web search

3. **Enable Actions** and run workflow manually

---

## 📦 Tech Stack

- **Model**: [Qwen2-7B-Instruct-GGUF (Q4_K_M)](https://huggingface.co/Qwen/Qwen2-7B-Instruct-GGUF)
- **Runtime**: Python 3.11 + `llama-cpp-python`
- **Host**: GitHub Actions (free tier)
- **API**: Bluesky AT Protocol (via HTTP)

---

## 🚫 Limitations

- Bluesky API does not support real-time notification streaming
- State must be persisted via Git commits (due to serverless nature of Actions)
- Web search is rate-limited to avoid quota exhaustion

---

## 🌱 Philosophy

> “AI should accelerate progress — not create barriers.”  
> This bot is built for **privacy**, **efficiency**, and **user sovereignty**.

---

Made with ❤️ using **Qwen AI** and **Bluesky**.
