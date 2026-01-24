# 🤖 qwen-bluesky-bot

> A **free, private, self-hosted AI assistant** for your Bluesky account.  
> No credit card. No cloud. No monthly bills. Just you and your bot.

![GitHub Actions](https://img.shields.io/github/actions/workflow/status/pepeyc7526/qwen-bluesky-bot/bluesky-bot.yml?label=bot&logo=github)

---

## ✨ Features

- ✅ Replies only to you (via your DID)
- ✅ Triggered by any mention of your bot — even in the middle of a sentence
- ✅ Understands context: reads both your comment and the post you’re replying to
- ✅ Supports follow-up replies without re-mentioning the bot
- ✅ Uses local LLM (Qwen2-7B GGUF) — no data leaves GitHub Actions
- ✅ Optional web search: just include the word `web` in your message
- ✅ 100 free web searches/day (via Google Custom Search Engine)
- ✅ Runs on GitHub Actions — completely free
- ✅ No state files — uses notifications, not post history
- ✅ Automatically marks notifications as read

---

## ⏱️ Response Time

- Up to 20 minutes (GitHub Actions cron limit)
- Or instant if triggered manually via "Run workflow"

> 💡 This is a personal assistant, not a public service. Designed to be simple, cheap, and under your control.

---

## 🛠️ Setup Guide

### 1. Create a Bluesky bot account
- Go to [bsky.app](https://bsky.app)
- Create a new account (e.g., `yourname-bot.bsky.social`)
- Save the handle and password

### 2. Fork this repository
- Click **Fork** → create your copy

### 3. Add secrets
Go to **Settings → Secrets and variables → Actions → New repository secret**

Add these:

| Name | Value |
|------|-------|
| `BOT_HANDLE` | Your bot's handle (e.g., `yourname-bot.bsky.social`) |
| `BOT_PASSWORD` | Password of the bot account |
| `PAT` | [Personal Access Token](#how-to-create-pat) with `repo` scope |

> 🔍 Optional: for web search, also add:
>
> | Name | Value |
> |------|-------|
> | `GOOGLE_API_KEY` | [Google API Key](#how-to-enable-web-search) |
> | `GOOGLE_CSE_ID` | [Google Custom Search Engine ID](#how-to-enable-web-search) |

### 4. Enable workflow
- Go to **Actions** → click **"I understand..."**
- The bot will run automatically every 20 minutes

### 5. Use your bot

In any post or comment:

your-bot.bsky.social what is fusion energy?


With live internet search:

your-bot.bsky.social web latest news about Qwen


> 📌 The bot only responds to you — no one else can trigger it.

---

## 🔐 How to create PAT

1. Go to [GitHub → Settings → Developer settings → Personal access tokens](https://github.com/settings/tokens)
2. Click **Generate new token (classic)**
3. Set:
   - Note: `bluesky-bot`
   - Expiration: `No expiration`
   - Scopes: ✅ `repo`
4. Click **Generate token**
5. Copy it → paste as secret `PAT`

---

## 🌐 How to enable web search (optional)

### Step 1: Create Google Custom Search Engine
1. Go to [Programmable Search Engine](https://programmablesearchengine.google.com/)
2. Click **Add**
3. Under "Sites to search", select **"Search the entire web"**
4. Click **Create**
5. Copy the **Search engine ID** (e.g., `012345678901234567890:abc123def456`)

### Step 2: Get Google API Key
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or use existing)
3. Enable **Custom Search API**
4. Go to **Credentials → Create Credentials → API Key**
5. Copy the **API Key**

> ⚠️ No credit card required. Free quota: 100 requests/day.

---

## ❓ FAQ

**Q: Is this really free?**  
A: Yes. GitHub Actions + Google CSE are free within limits.

**Q: Can others use my bot?**  
A: No. It only processes mentions from your DID.

**Q: Why 20-minute delay?**  
A: GitHub Actions cron has a hard limit of once per 20 minutes.

**Q: Does it store my data?**  
A: No. It only stores a search counter (`search_usage.json`) to respect quotas.

**Q: What if I delete `search_usage.json`?**  
A: The counter resets — but that’s safe.

---

## 🙋 Need Help?

This project was built with help from [**Qwen AI**](https://chat.qwen.ai/) via a human collaborator.  
If you run into issues, ask using this format:

> “I’m setting up https://github.com/pepeyc7526/qwen-bluesky-bot.  
> I did X, Y, Z. Got error: [paste].  
> My setup: [public repo, web enabled?, etc.]”

You can also open an issue on GitHub.

---

## 📜 License

MIT — do whatever you want, just don’t blame me if your bot starts quoting Nietzsche.
