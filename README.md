# 🤖 Bluesky AI Bot (Qwen2 + Web Search)

> A **free, private, self-hosted AI assistant** for your Bluesky account.  
> No credit card. No cloud. No monthly bills. Just you and your bot.

![GitHub Actions](https://img.shields.io/github/actions/workflow/status/pepeyc7526/bluesky-ai-bot/bluesky-bot.yml?label=bot&logo=github)

---

## ✨ Features

- ✅ Answers **only to you**
- ✅ Uses **local LLM** (Qwen2-7B) — no data leaves your workflow
- ✅ Optional **web search**: just type `ai web ...`
- ✅ **100 free web searches/day** (via Google CSE)
- ✅ Runs on **GitHub Actions** — completely free
- ✅ No external servers, no subscriptions

---

## ⏱️ Response Time

- **Up to 20 minutes** (due to GitHub Actions cron limit)
- Or **instant** if you trigger manually via "Run workflow"

> 💡 This is a **personal assistant**, not a public service. It’s designed to be simple, cheap, and under your control.

---

## 🛠️ Setup Guide

### 1. Create a Bluesky bot account
- Go to [bsky.app](https://bsky.app)
- Create a new account (e.g., `yourname-bot.bsky.social`)
- Save the **handle** and **password**

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

> 🔍 **Optional**: for web search, also add:
>
> | Name | Value |
> |------|-------|
> | `GOOGLE_API_KEY` | [Google API Key](#how-to-enable-web-search) |
> | `GOOGLE_CSE_ID` | [Google Custom Search Engine ID](#how-to-enable-web-search) |

### 4. Enable workflow
- Go to **Actions** → click **"I understand..."**
- The bot will run automatically every 20 minutes

### 5. Use your bot
Post from **your main account**:

- `ai What is AI?` → local answer
- `ai web What is Chainbase?` → with web search

> 📌 The bot **only responds to you** — no one else can trigger it.

---

## 🔐 How to create PAT

1. Go to [GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)](https://github.com/settings/tokens)
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
5. Copy the **Search engine ID** (looks like `012345678901234567890:abc123def456`)

### Step 2: Get Google API Key
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or use existing)
3. Enable **Custom Search API**:
   - Search for "Custom Search API" → Enable
4. Go to **Credentials → Create Credentials → API Key**
5. Copy the **API Key**

> ⚠️ No credit card required. Free quota: **100 requests/day**.

---

## ❓ FAQ

**Q: Is this really free?**  
A: Yes. GitHub Actions + Google CSE are free within limits.

**Q: Can others use my bot?**  
A: No. It only reads **your posts** (via your DID).

**Q: Why 20-minute delay?**  
A: GitHub Actions cron has a hard limit of once per 20 minutes.

**Q: Can I make it faster?**  
A: Only by triggering manually or using a paid server (not recommended for personal use).

---

## 🙋 Need Help?

This project was built with help from **Qwen AI** via a human collaborator.  
If you run into issues, you can ask for help using this prompt:

> “I’m setting up the Bluesky AI Bot from https://github.com/pepeyc7526/bluesky-ai-bot.  
> I’ve done [steps X, Y, Z], but [describe issue].  
> Here’s my log/error: [paste].  
> My setup: [public/private repo, web search enabled?, etc.]”

This gives enough context to debug quickly — no guesswork needed.

You can also open an issue on GitHub.

---

## 📜 License

MIT — do whatever you want, just don’t blame me if your bot starts quoting Nietzsche.
