#!/usr/bin/env python3
import os, json, datetime, asyncio, httpx

# Configuration
BOT_TOKEN = os.getenv("BLUESKY_TOKEN")
LUMO_API_KEY = os.getenv("LUMO_API_KEY", "")
OWNER_DID = "did:plc:topho472iindqxv5hm7nzww2"  # ваш DID
MAX_LEN = 300
ELLIPSIS = "…"

STATE_FILE = "state.json"

if not BOT_TOKEN:
    raise RuntimeError("BLUESKY_TOKEN is required")

# Load last processed URI
def load_last_uri():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f).get("last_uri", "")
    return ""

def save_last_uri(uri):
    with open(STATE_FILE, "w") as f:
        json.dump({"last_uri": uri}, f)

async def get_author_feed(did: str):
    url = f"https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed?actor={did}&limit=10"
    async with httpx.AsyncClient() as client:
        r = await client.get(url)
        return r.json()

async def ask_lumo(prompt: str) -> str:
    headers = {"Content-Type": "application/json"}
    if LUMO_API_KEY:
        headers["Authorization"] = f"Bearer {LUMO_API_KEY}"
    payload = {
        "model": "lumo-1.2",
        "messages": [{"role": "user", "content": prompt}]
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://api.lumo.proton.me/v1/chat/completions",
            headers=headers,
            json=payload,
        )
        data = r.json()
        answer = data["choices"][0]["message"]["content"]
    answer = " ".join(answer.split())
    if len(answer) > MAX_LEN:
        answer = answer[: MAX_LEN - len(ELLIPSIS)] + ELLIPSIS
    return answer

async def post_reply(text: str):
    url = "https://bsky.social/xrpc/com.atproto.repo.createRecord"
    payload = {
        "$type": "app.bsky.feed.post",
        "text": text,
        "createdAt": datetime.datetime.utcnow().isoformat() + "Z"
    }
    async with httpx.AsyncClient() as client:
        await client.post(
            url,
            headers={
                "Authorization": f"Bearer {BOT_TOKEN}",
                "Content-Type": "application/json"
            },
            json=payload,
        )

async def main():
    last_uri = load_last_uri()
    feed = await get_author_feed(OWNER_DID)
    
    for item in feed.get("feed", []):
        post = item.get("post", {})
        uri = post.get("uri", "")
        text = post.get("record", {}).get("text", "")

        # Пропустить, если уже обработан
        if uri == last_uri:
            break

        # Проверить команду
        if text.lower().strip().startswith("check"):
            content = text[len("check"):].strip()
            if content:
                prompt = (
                    "Provide a concise fact-check of the following claim. "
                    "Respond in under 300 characters, without links or emojis.\n\n"
                    f"{content}"
                )
                reply = await ask_lumo(prompt)
                await post_reply(reply)
                print(f"[{datetime.datetime.utcnow()}] Replied to {uri}")
                save_last_uri(uri)
                return  # обрабатываем только самый свежий

if __name__ == "__main__":
    asyncio.run(main())