# 🤖 Qwen2 Bluesky AI Bot

A private, self-hosted AI assistant for [Bluesky](https://bsky.app) that runs **100% locally** using the **Qwen2-7B** model.  
No external APIs. No data leaks. Fully under your control.

---

## ✨ Features

- ✅ **Private & local**: Runs on GitHub Actions with **no cloud costs**
- ✅ **Free**: Uses open-source **Qwen2-7B GGUF** (4-bit quantized)
- ✅ **Context-aware**: Understands replies to its own posts
- ✅ **Natural behavior**: Random 1–2 min delays between replies (avoids spam detection)
- ✅ **Web search** (optional): Type `web <query>` to trigger live search
- ✅ **Monthly quota**: Web search limited to avoid API exhaustion
- ✅ **Persistent memory**: Remembers last processed notification via `last_processed.json`

---

## 💬 How to Use

The bot responds **only to you** (verified by your DID). You can:

- **Mention it**:  
  `@your-bot.bsky.social what is fusion?`

- **Reply to its posts** (no mention needed):  
  Just write `explain more` under its post

- **Use web search**:  
  `@your-bot.bsky.social web what is chainbase.com?`

> ⚠️ Web search requires valid `GOOGLE_API_KEY` and `GOOGLE_CSE_ID` in secrets.

---

## 🔐 Setup

1. **Fork this repo**
2. Add these **secrets** in `Settings → Secrets and variables → Actions`:
   - `BOT_HANDLE` — your bot’s Bluesky handle (e.g. `bot-pepeyc7526.bsky.social`)
   - `BOT_PASSWORD` — app password (generate in Bluesky settings)
   - `BOT_DID` — your bot’s DID (find via `atproto identity resolve`)
   - `OWNER_DID` — your personal DID (`did:plc:000000000000000000000000`)
   - `PAT` — GitHub Personal Access Token with `repo` scope (for committing state)
   - *(Optional)* `GOOGLE_API_KEY` & `GOOGLE_CSE_ID` — for web search

3. **Enable Actions** and run workflow manually

> 💡 The bot will auto-create `last_processed.json` and `search_usage.json` on first run.

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
- Web search is rate-limited to **~100 queries/month** (reset automatically)

---

## 🌱 Philosophy

> “AI should accelerate progress — not create barriers.”  
> This bot is built for **privacy**, **efficiency**, and **user sovereignty**.

---

## 📜 License

MIT License

Copyright (c) 2026 pepeyc7526

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---

Made with ❤️ using **Qwen AI** and **Bluesky**.
