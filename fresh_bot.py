#!/usr/bin/env python3
import os, json, datetime, asyncio, httpx
from llama_cpp import Llama

BOT_HANDLE    = os.getenv("BOT_HANDLE", "bot-pepeyc7526.bsky.social")
BOT_PASSWORD  = os.getenv("BOT_PASSWORD")
BOT_DID       = "did:plc:er457dupy7iytuzdgfmfsuv7"
OWNER_DID     = "did:plc:topho472iindqxv5hm7nzww2"
MAX_LEN       = 300
LAST_POST_FILE = "last_processed_post.txt"

MODEL_PATH = "models/qwen2-7b-instruct-q4_k_m.gguf"
llm = Llama(model_path=MODEL_PATH, n_ctx=2048, n_threads=2, verbose=False)

if not BOT_PASSWORD:
    raise RuntimeError("BOT_PASSWORD missing")

def get_last_processed_uri():
    if os.path.exists(LAST_POST_FILE):
        with open(LAST_POST_FILE, "r") as f:
            return f.read().strip()
    return None

def save_last_processed_uri(uri):
    with open(LAST_POST_FILE, "w") as f:
        f.write(uri)

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
    messages = [
        {"role": "system", "content": "You are a helpful AI assistant. Give short, clear answers under 300 characters. Never use links or emojis."},
        {"role": "user", "content": prompt}
    ]
    
    full_prompt = ""
    for msg in messages:
        if msg["role"] == "user":
            full_prompt += f"<|im_start|>user\n{msg['content']}<|im_end|>\n"
        elif msg["role"] == "assistant":
            full_prompt += f"<|im_start|>assistant\n{msg['content']}<|im_end|>\n"
        else:
            full_prompt += f"<|im_start|>system\n{msg['content']}<|im_end|>\n"
    full_prompt += "<|im_start|>assistant\n"

    out = llm(
        full_prompt,
        max_tokens=120,
        stop=["<|im_end|>", "<|im_start|>"],
        echo=False,
        temperature=0.3
    )
    ans = out["choices"][0]["text"].strip()
    ans = " ".join(ans.split())

    if any(w in ans.lower() for w in ["don't know", "unclear", "provide more", "doesn't seem", "not recognized"]):
        ans = "🤔 Not sure what you mean. Try rephrasing!"

    return ans[:MAX_LEN] if len(ans) > MAX_LEN else ans

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

    last_uri = get_last_processed_uri()
    print(f"⏭️ Skipping posts before: {last_uri}")

    feed = await get_author_feed(OWNER_DID, token)
    replied_uri = None

    for item in feed[:10]:
        post = item.get("post", {})
        record = post.get("record", {})
        if record.get("$type") != "app.bsky.feed.post":
            continue

        uri = post.get("uri", "")
        if not uri:
            continue

        if last_uri and uri == last_uri:
            break

        txt = record.get("text", "")
        clean_txt = txt.strip()

        replied = False

        if clean_txt.lower().startswith("ai"):
            content = clean_txt[2:].strip()
            if content:
                print(f"👤 'ai' request: {content[:50]}...")
                prompt = f"User request: {content}"
                reply = ask_local(prompt)
                await post_reply(reply, uri, token)
                print(f"✅ Replied to {uri}")
                replied_uri = uri
                replied = True

        elif clean_txt.startswith("@bot-pepeyc7526.bsky.social"):
            content = clean_txt[len("@bot-pepeyc7526.bsky.social"):].strip()
            if content:
                print(f"👤 '@bot' request: {content[:50]}...")
                prompt = f"User request: {content}"
                reply = ask_local(prompt)
                await post_reply(reply, uri, token)
                print(f"✅ Replied to {uri}")
                replied_uri = uri
                replied = True

        if replied:
            break

    if replied_uri:
        save_last_processed_uri(replied_uri)
        print(f"💾 Saved last processed URI: {replied_uri}")

    seen_at = datetime.datetime.utcnow().isoformat() + "Z"
    await mark_as_read(token, seen_at)
    print("✅ Done")

if __name__ == "__main__":
    asyncio.run(main())
