#!/usr/bin/env python3
import os, json, datetime, asyncio, httpx
from llama_cpp import Llama

BOT_HANDLE    = os.getenv("BOT_HANDLE", "bot-pepeyc7526.bsky.social")
BOT_PASSWORD  = os.getenv("BOT_PASSWORD")
BOT_DID       = "did:plc:er457dupy7iytuzdgfmfsuv7"
OWNER_DID     = "did:plc:topho472iindqxv5hm7nzww2"
MAX_LEN       = 300
ELLIPSIS      = "…"

MODEL_PATH = "models/Phi-3-mini-4k-instruct-q4.gguf"
llm = Llama(model_path=MODEL_PATH, n_ctx=2048, n_threads=2, verbose=False)

if not BOT_PASSWORD:
    raise RuntimeError("BOT_PASSWORD missing")

async def get_fresh_token() -> str:
    url = "https://bsky.social/xrpc/com.atproto.server.createSession"
    payload = {"identifier": BOT_HANDLE, "password": BOT_PASSWORD}
    async with httpx.AsyncClient() as client:
        r = await client.post(url, json=payload)
        return r.json()["accessJwt"]

async def post_to_bluesky(text: str, token: str):
    url = "https://bsky.social/xrpc/com.atproto.repo.createRecord"
    payload = {
        "repo": BOT_DID,
        "collection": "app.bsky.feed.post",
        "record": {
            "$type": "app.bsky.feed.post",
            "text": text,
            "createdAt": datetime.datetime.utcnow().isoformat() + "Z"
        }
    }
    async with httpx.AsyncClient() as client:
        await client.post(url, headers={"Authorization": f"Bearer {token}"}, json=payload)

async def get_record_cid(uri: str, token: str):
    try:
        parts = uri.split("/")
        repo, collection, rkey = parts[2], parts[3], parts[4]
        url = f"https://bsky.social/xrpc/com.atproto.repo.getRecord?repo={repo}&collection={collection}&rkey={rkey}"
        async with httpx.AsyncClient() as client:
            r = await client.get(url, headers={"Authorization": f"Bearer {token}"})
            return r.json()["cid"]
    except Exception:
        return "bafyreihjdbd4zq4f4a5v6w5z5g5q5j5j5j5j5j5j5j5j5j5j5j5j5j5j5j5j5j"

async def get_post_text(uri: str, token: str) -> str:
    try:
        parts = uri.split("/")
        repo, rkey = parts[2], parts[4]
        url = f"https://bsky.social/xrpc/com.atproto.repo.getRecord?repo={repo}&collection=app.bsky.feed.post&rkey={rkey}"
        async with httpx.AsyncClient() as client:
            r = await client.get(url, headers={"Authorization": f"Bearer {token}"})
            return r.json()["value"]["text"]
    except Exception:
        return ""

async def get_notifications(token: str):
    url = "https://bsky.social/xrpc/app.bsky.notification.listNotifications"
    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers={"Authorization": f"Bearer {token}"})
        return r.json().get("notifications", [])

async def mark_as_read(token: str, seen_at: str):
    url = "https://bsky.social/xrpc/app.bsky.notification.updateSeen"
    payload = {"seenAt": seen_at}
    async with httpx.AsyncClient() as client:
        await client.post(url, headers={"Authorization": f"Bearer {token}"}, json=payload)

def ask_local(prompt: str) -> str:
    full_prompt = (
        "<|user|>\nProvide a concise answer or fact-check based on the context. "
        "Respond in under 300 characters, without links or emojis.\n\n"
        f"{prompt}\n<|end|>\n<|assistant|>\n"
    )
    out = llm(full_prompt, max_tokens=100, stop=["<|end|>", "<|user|>"], echo=False, temperature=0.3)
    ans = out["choices"][0]["text"].strip()
    ans = " ".join(ans.split())
    return ans[:MAX_LEN - len(ELLIPSIS)] + ELLIPSIS if len(ans) > MAX_LEN else ans

async def post_reply(text: str, reply_to_uri: str, token: str):
    cid = await get_record_cid(reply_to_uri, token)
    url = "https://bsky.social/xrpc/com.atproto.repo.createRecord"
    payload = {
        "repo": BOT_DID,
        "collection": "app.bsky.feed.post",
        "record": {
            "$type": "app.bsky.feed.post",
            "text": text,
            "reply": {
                "root": {"uri": reply_to_uri, "cid": cid},
                "parent": {"uri": reply_to_uri, "cid": cid}
            },
            "createdAt": datetime.datetime.utcnow().isoformat() + "Z"
        }
    }
    async with httpx.AsyncClient() as client:
        await client.post(url, headers={"Authorization": f"Bearer {token}"}, json=payload)

async def main():
    token = await get_fresh_token()
    print("✅ Checking for mentions...")

    notifications = await get_notifications(token)
    print(f"📥 Found {len(notifications)} notifications")

    for notif in notifications:
        if notif.get("reason") != "mention":
            continue

        record = notif.get("record", {})
        if record.get("$type") != "app.bsky.feed.post":
            continue

        txt = record.get("text", "")
        uri = notif.get("uri", "")  # ← КЛЮЧЕВОЕ ИЗМЕНЕНИЕ

        if not uri:
            print("   ⚠️ Skipped: no URI")
            continue

        # Удаляем упоминание бота из текста
        clean_txt = txt
        bot_mention = "@bot-pepeyc7526.bsky.social"
        if clean_txt.startswith(bot_mention):
            clean_txt = clean_txt[len(bot_mention):].strip()

        if not clean_txt:
            continue

        print(f"🎯 Processing: {clean_txt[:50]}...")
        try:
            parent_text = ""
            if "reply" in record and "parent" in record["reply"]:
                parent_uri = record["reply"]["parent"]["uri"]
                parent_text = await get_post_text(parent_uri, token)
                prompt = f"Parent post: {parent_text}\nUser question: {clean_txt}"
            else:
                prompt = f"User question: {clean_txt}"

            reply = ask_local(prompt)
            await post_reply(reply, uri, token)
            print(f"✅ Replied to {uri}")

        except Exception as e:
            print(f"[ERROR] {e}")

    seen_at = datetime.datetime.utcnow().isoformat() + "Z"
    await mark_as_read(token, seen_at)
    print("✅ All notifications marked as read")

if __name__ == "__main__":
    asyncio.run(main())
