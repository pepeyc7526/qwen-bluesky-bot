# 🤖 Qwen2 Bluesky AI Bot

A private, self-hosted AI assistant for [Bluesky](https://bsky.app) powered by the open-source **Qwen2-7B** model.  
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
