#!/usr/bin/env python3
import os, json, datetime, asyncio, httpx, random
from llama_cpp import Llama

BOT_HANDLE    = os.getenv("BOT_HANDLE")
BOT_PASSWORD  = os.getenv("BOT_PASSWORD")
BOT_DID       = os.getenv("BOT_DID")
OWNER_DID     = os.getenv("OWNER_DID")
MAX_LEN       = 300
SEARCH_USAGE_FILE = "search_usage.json"

if not all([BOT_HANDLE, BOT_PASSWORD, BOT_DID, OWNER_DID]):
    raise RuntimeError("Missing required env vars: BOT_HANDLE, BOT_PASSWORD, BOT_DID, OWNER_DID")

MODEL_PATH = "models/qwen2-7b-instruct-q4_k_m.gguf"
llm = Llama(model_path=MODEL_PATH, n_ctx=2048, n_threads=2, verbose=False)

def load_search_usage():
    if os.path.exists(SEARCH_USAGE_FILE):
        with open(SEARCH_USAGE_FILE, "r") as f:
            return json.load(f)
    return {"count": 0, "month": datetime.datetime.now().month}

def save_search_usage(count: int):
    data = {"count": count, "month": datetime.datetime.now().month}
    with open(SEARCH_USAGE_FILE, "w") as f:
        json.dump(data, f)

def should_reset_counter():
    usage = load_search_usage()
    current_month = datetime.datetime.now().month
    return usage["month"] != current_month

async def get_fresh_token() -> str:
    url = "https://bsky.social/xrpc/com.atproto.server.createSession"
    payload = {"identifier": BOT_HANDLE, "password": BOT_PASSWORD}
    async with httpx.AsyncClient() as client:
        r = await client.post(url, json=payload)
        return r.json()["accessJwt"]

async def post_reply(text: str, reply_to_uri: str, token: str):
    try:
        parts = reply_to_uri.split("/")
        repo, collection, rkey = parts[2], parts[3], parts[4]
        url = f"https://bsky.social/xrpc/com.atproto.repo.getRecord?repo={repo}&collection={collection}&rkey={rkey}"
        async with httpx.AsyncClient() as client:
            r = await client.get(url, headers={"Authorization": f"Bearer {token}"})
            cid = r.json()["cid"]
    except Exception as e:
        print(f"[CID ERROR] {e}")
        cid = "bafyreihjdbd4zq4f4a5v6w5z5g5q5j5j5j5j5j5j5j5j5j5j5j5j5j5j5j5j5j"

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

async def get_parent_post_text(uri: str, token: str) -> str:
    try:
        parts = uri.split("/")
        repo, rkey = parts[2], parts[4]
        url = f"https://bsky.social/xrpc/com.atproto.repo.getRecord?repo={repo}&collection=app.bsky.feed.post&rkey={rkey}"
        async with httpx.AsyncClient() as client:
            r = await client.get(url, headers={"Authorization": f"Bearer {token}"})
            record = r.json().get("value", {})
            reply = record.get("reply")
            if not reply or "parent" not in reply:
                return ""
            parent_uri = reply["parent"]["uri"]
            parent_parts = parent_uri.split("/")
            parent_repo, parent_rkey = parent_parts[2], parent_parts[4]
            parent_url = f"https://bsky.social/xrpc/com.atproto.repo.getRecord?repo={parent_repo}&collection=app.bsky.feed.post&rkey={parent_rkey}"
            r2 = await client.get(parent_url, headers={"Authorization": f"Bearer {token}"})
            parent_record = r2.json().get("value", {})
            return parent_record.get("text", "")
    except Exception as e:
        print(f"[PARENT ERROR] {e}")
        return ""

def ask_local(prompt: str) -> str:
    messages = [
        {"role": "system", "content": "You are a helpful AI assistant. Answer briefly and clearly. Keep under 300 chars. No links or emojis."},
        {"role": "user", "content": prompt}
    ]
    
    full_prompt = ""
    for msg in messages:
        if msg["role"] == "user":
            full_prompt += "  <|im_start|>user\n" + msg['content'] + "<|im_end|>\n"
        elif msg["role"] == "assistant":
            full_prompt += "  <|im_start|>assistant\n" + msg['content'] + "<|im_end|>\n"
        else:
            full_prompt += "  <|im_start|>system\n" + msg['content'] + "<|im_end|>\n"
    full_prompt += "  <|im_start|>assistant\n"

    out = llm(
        full_prompt,
        max_tokens=120,
        stop=["<|im_end|>", "<|im_start|>"],
        echo=False,
        temperature=0.3
    )
    ans = out["choices"][0]["text"].strip()
    ans = " ".join(ans.split())

    if any(w in ans.lower() for w in ["don't know", "unclear", "provide more", "doesn't seem"]):
        ans = "🤔 Not sure what you mean. Try rephrasing!"

    return ans[:MAX_LEN] if len(ans) > MAX_LEN else ans

async def mark_notification_as_read(token: str, seen_at: str):
    url = "https://bsky.social/xrpc/app.bsky.notification.updateSeen"
    payload = {"seenAt": seen_at}
    async with httpx.AsyncClient() as client:
        await client.post(url, headers={"Authorization": f"Bearer {token}"}, json=payload)

async def main():
    token = await get_fresh_token()
    print("✅ Checking notifications...")

    if should_reset_counter():
        save_search_usage(0)
        print("📅 Search counter reset")

    url = "https://bsky.social/xrpc/app.bsky.notification.listNotifications"
    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers={"Authorization": f"Bearer {token}"})
        notifications = r.json().get("notifications", [])

    print(f"📥 Found {len(notifications)} unread notifications")

    for notif in notifications:
        author_did = notif.get("author", {}).get("did", "")
        if author_did != OWNER_DID:
            continue

        reason = notif.get("reason")
        if reason not in ("mention", "reply"):
            continue

        record = notif.get("record", {})
        if record.get("$type") != "app.bsky.feed.post":
            continue

        txt = record.get("text", "").strip()
        if not txt:
            continue

        uri = notif.get("uri", "")
        indexed_at = notif.get("indexedAt")

        print(f"\n🔍 Processing notification: {indexed_at}")
        print(f"   Reason: {reason}")
        print(f"   Text: '{txt}'")

        parent_text = await get_parent_post_text(uri, token)
        if parent_text:
            prompt = f"User replied to this message: '{parent_text}'. Their comment: '{txt}'. Provide a helpful response."
        else:
            prompt = f"User says: '{txt}'. Respond helpfully."

        reply = ask_local(prompt)
        await post_reply(reply, uri, token)
        print(f"✅ Replied: '{reply}'")

        # ✅ Mark this notification as read IMMEDIATELY after replying
        await mark_notification_as_read(token, indexed_at)
        print(f"✅ Marked as read")

        delay = random.randint(60, 120)
        print(f"⏳ Waiting {delay} seconds before next reply...")
        await asyncio.sleep(delay)

    print("✅ All unread notifications processed")

if __name__ == "__main__":
    asyncio.run(main())
