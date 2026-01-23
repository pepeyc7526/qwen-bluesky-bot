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

async def get_author_feed(author_did: str, token: str):
    url = "https://bsky.social/xrpc/app.bsky.feed.getAuthorFeed"
    params = {"actor": author_did}
    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers={"Authorization": f"Bearer {token}"}, params=params)
        return r.json().get("feed", [])

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
    print("✅ Checking only YOUR requests...")

    # Читаем только твои посты
    feed = await get_author_feed(OWNER_DID, token)
    for item in feed[:5]:  # последние 5 постов
        post = item.get("post", {})
        record = post.get("record", {})
        if record.get("$type") != "app.bsky.feed.post":
            continue

        txt = record.get("text", "")
        uri = post.get("uri", "")

        clean_txt = txt.strip()
        replied = False

        # Вариант 1: начинается с "ai"
        if clean_txt.lower().startswith("ai"):
            content = clean_txt[2:].strip()
            if content:
                print(f"👤 'ai' request: {content[:50]}...")
                prompt = f"User request: {content}"
                reply = ask_local(prompt)
                await post_reply(reply, uri, token)
                print(f"✅ Replied to {uri}")
                replied = True

        # Вариант 2: начинается с упоминания бота
        elif clean_txt.startswith("@bot-pepeyc7526.bsky.social"):
            content = clean_txt[len("@bot-pepeyc7526.bsky.social"):].strip()
            if content:
                print(f"👤 '@bot' request: {content[:50]}...")
                prompt = f"User request: {content}"
                reply = ask_local(prompt)
                await post_reply(reply, uri, token)
                print(f"✅ Replied to {uri}")
                replied = True

        if replied:
            break  # отвечаем только на самый свежий запрос

    seen_at = datetime.datetime.utcnow().isoformat() + "Z"
    await mark_as_read(token, seen_at)
    print("✅ Done")

if __name__ == "__main__":
    asyncio.run(main())
