#!/usr/bin/env python3
import os, json, datetime, asyncio, httpx

# ---------- CONFIGURATION ----------
BLUESKY_TOKEN = os.getenv("BLUESKY_TOKEN")          # token of the BOT account
LUMO_API_KEY  = os.getenv("LUMO_API_KEY", "")
BOT_HANDLE    = "lumobot-pepeyc7526.bsky.social"    # handle of the BOT account
BOT_DID       = "did:plc:er457dupy7iytuzdgfmfsuv7"  # DID of the BOT account
OWNER_DID     = "did:plc:topho472iindqxv5hm7nzww2" # your DID (to allow direct commands)
MAX_LEN       = 300
ELLIPSIS      = "…"
# ------------------------------------

if not BLUESKY_TOKEN:
    raise RuntimeError("BLUESKY_TOKEN missing – add it as a secret")

async def bluesky_stream():
    url = "https://bsky.social/xrpc/com.atproto.sync.subscribeRepos"
    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream(
            "GET", url,
            headers={"Authorization": f"Bearer {BLUESKY_TOKEN}"}
        ) as resp:
            async for line in resp.aiter_lines():
                if not line.strip():
                    continue
                try:
                    ev = json.loads(line)
                except Exception:
                    continue
                if ev.get("$type") != "com.atproto.sync.subscribeRepos#commit":
                    continue
                for op in ev.get("ops", []):
                    if op.get("$type") != "app.bsky.feed.post":
                        continue
                    rec = op.get("payload", {})
                    txt = rec.get("text", "")
                    uri = rec.get("uri", "")
                    author = rec.get("author", {})
                    author_did = author.get("did", "")

                    # Check if post contains @bot AND starts with "check"
                    if f"@{BOT_HANDLE}" not in txt.lower() and author_did != OWNER_DID:
                        continue

                    if not txt.lower().strip().startswith("check"):
                        continue

                    yield txt, uri, author_did

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

async def post_reply(text: str, reply_to_uri: str):
    url = "https://bsky.social/xrpc/com.atproto.repo.createRecord"
    payload = {
        "$type": "app.bsky.feed.post",
        "text": text,
        "reply": {
            "root": {"uri": reply_to_uri, "cid": "PLACEHOLDER_CID"},  # CID needs to be fetched separately
            "parent": {"uri": reply_to_uri, "cid": "PLACEHOLDER_CID"}
        },
        "createdAt": datetime.datetime.utcnow().isoformat() + "Z"
    }
    async with httpx.AsyncClient() as client:
        await client.post(
            url,
            headers={
                "Authorization": f"Bearer {BLUESKY_TOKEN}",
                "Content-Type": "application/json"
            },
            json=payload,
        )

async def main():
    async for txt, uri, author_did in bluesky_stream():
        content = txt[len("check"):].strip()
        if not content:
            continue

        prompt = (
            "Provide a concise fact-check of the following claim. "
            "Respond in under 300 characters, without links or emojis.\n\n"
            f"{content}"
        )
        reply = await ask_lumo(prompt)
        await post_reply(reply, uri)  # Reply to the original post/comment
        print(f"[{datetime.datetime.utcnow()}] Replied to {uri} by {author_did}")

if __name__ == "__main__":
    asyncio.run(main())
