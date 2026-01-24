#!/usr/bin/env python3
import os, json, datetime, asyncio, httpx, random
from llama_cpp import Llama

BOT_HANDLE    = os.getenv("BOT_HANDLE")
BOT_PASSWORD  = os.getenv("BOT_PASSWORD")
BOT_DID       = os.getenv("BOT_DID")
OWNER_DID     = os.getenv("OWNER_DID")
MAX_LEN       = 300
SEARCH_USAGE_FILE = "search_usage.json"
LAST_PROCESSED_FILE = "last_processed.json"

if not all([BOT_HANDLE, BOT_PASSWORD, BOT_DID, OWNER_DID]):
    raise RuntimeError("Missing required env vars: BOT_HANDLE, BOT_PASSWORD, BOT_DID, OWNER_DID")

MODEL_PATH = "models/qwen2-7b-instruct-q4_k_m.gguf"
llm = Llama(model_path=MODEL_PATH, n_ctx=2048, n_threads=2, verbose=False)

def load_last_processed():
    if os.path.exists(LAST_PROCESSED_FILE):
        with open(LAST_PROCESSED_FILE, "r") as f:
            return json.load(f).get("indexedAt", "1970-01-01T00:00:00.000Z")
    return "1970-01-01T00:00:00.000Z"

def save_last_processed(indexed_at):
    with open(LAST_PROCESSED_FILE, "w") as f:
        json.dump({"indexedAt": indexed_at}, f)

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
        r = await client.post(url, json=payload, timeout=30.0)
        return r.json()["accessJwt"]

async def post_reply(text: str, reply_to_uri: str, token: str):
    try:
        # Extract CID for the post we're replying to
        parts = reply_to_uri.split("/")
        repo, collection, rkey = parts[2], parts[3], parts[4]
        url = f"https://bsky.social/xrpc/com.atproto.repo.getRecord?repo={repo}&collection={collection}&rkey={rkey}"
        async with httpx.AsyncClient() as client:
            r = await client.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=30.0)
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
        await client.post(url, headers={"Authorization": f"Bearer {token}"}, json=payload, timeout=30.0)

async def get_parent_post_text(uri: str, token: str) -> str:
    try:
        parts = uri.split("/")
        repo, rkey = parts[2], parts[4]
        url = f"https://bsky.social/xrpc/com.atproto.repo.getRecord?repo={repo}&collection=app.bsky.feed.post&rkey={rkey}"
        async with httpx.AsyncClient() as client:
            r = await client.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=30.0)
            record = r.json().get("value", {})
            reply = record.get("reply")
            if not reply or "parent" not in reply:
                return ""
            parent_uri = reply["parent"]["uri"]
            parent_parts = parent_uri.split("/")
            parent_repo, parent_rkey = parent_parts[2], parent_parts[4]
            parent_url = f"https://bsky.social/xrpc/com.atproto.repo.getRecord?repo={parent_repo}&collection=app.bsky.feed.post&rkey={parent_rkey}"
            r2 = await client.get(parent_url, headers={"Authorization": f"Bearer {token}"}, timeout=30.0)
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
            full_prompt += "                              <im_start>user\n" + msg['content'] + "<im_end>\n"
        elif msg["role"] == "assistant":
            full_prompt += "                              <im_start>assistant\n" + msg['content'] + "<im_end>\n"
        else:
            full_prompt += "                              <im_start>system\n" + msg['content'] + "<im_end>\n"
    full_prompt += "                              <im_start>assistant\n"

    out = llm(
        full_prompt,
        max_tokens=120,
        stop=["<im_end>", "<im_start>"],
        echo=False,
        temperature=0.3
    )
    ans = out["choices"][0]["text"].strip()
    ans = " ".join(ans.split())

    if any(w in ans.lower() for w in ["don't know", "unclear", "provide more", "doesn't seem"]):
        ans = "🤔 Not sure what you mean. Try rephrasing!"

    return ans[:MAX_LEN] if len(ans) > MAX_LEN else ans

async def mark_notifications_as_read(token: str, seen_at: str):
    url = "https://bsky.social/xrpc/app.bsky.notification.updateSeen"
    payload = {"seenAt": seen_at}
    async with httpx.AsyncClient() as client:
        await client.post(url, headers={"Authorization": f"Bearer {token}"}, json=payload, timeout=30.0)

async def main():
    token = await get_fresh_token()
    print("✅ Starting bot...")

    if should_reset_counter():
        save_search_usage(0)
        print("📅 Search counter reset")

    # Load last processed time
    last_indexed_at = load_last_processed()
    print(f"🕒 Last processed notification: {last_indexed_at}")

    # Fetch notifications
    url = "https://bsky.social/xrpc/app.bsky.notification.listNotifications"
    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=30.0)
        notifications = r.json().get("notifications", [])

    print(f"📥 Found {len(notifications)} notifications from API")
    
    # Log all notifications for debugging
    print("\n📋 ALL NOTIFICATIONS DEBUG:")
    for i, notif in enumerate(notifications):
        indexed_at = notif.get("indexedAt", "N/A")
        author = notif.get("author", {}).get("handle", "N/A")
        reason = notif.get("reason", "N/A")
        text = notif.get("record", {}).get("text", "")[:50] + "..." if notif.get("record") else "N/A"
        is_read = notif.get("isRead", False)
        print(f"{i+1}. [{indexed_at}] @{author} | {reason} | read:{is_read} | '{text}'")

    # Filter: only new notifications from owner with valid content
    new_notifs = []
    for notif in notifications:
        indexed_at = notif.get("indexedAt", "")
        author_did = notif.get("author", {}).get("did", "")
        reason = notif.get("reason", "")
        record = notif.get("record", {})
        txt = record.get("text", "").strip() if record else ""
        uri = notif.get("uri", "")

        if not indexed_at:
            print(f"❌ Skipped: no indexedAt - {indexed_at}")
            continue
            
        if not txt:
            print(f"❌ Skipped: empty text - '{txt}'")
            continue
            
        if not uri:
            print(f"❌ Skipped: no URI")
            continue
            
        if indexed_at <= last_indexed_at:
            print(f"❌ Skipped: not new (last processed: {last_indexed_at})")
            continue
            
        if author_did != OWNER_DID:
            print(f"❌ Skipped: not from owner (author: {author_did})")
            continue
            
        if record.get("$type") != "app.bsky.feed.post":
            print(f"❌ Skipped: not a post (type: {record.get('$type')})")
            continue

        # Log accepted notification
        print(f"✅ ACCEPTED: {reason} | {indexed_at} | '{txt[:30]}...'")
        new_notifs.append((notif, indexed_at))

    print(f"\n🔍 Found {len(new_notifs)} valid notifications to process")

    if not new_notifs:
        # Still mark latest notification as read to reset UI counter
        if notifications:
            latest = max(notifications, key=lambda x: x.get("indexedAt", ""))
            await mark_notifications_as_read(token, latest.get("indexedAt", ""))
            print(f"✅ UI counter reset (marked up to {latest.get('indexedAt')})")
        else:
            print("ℹ️ No notifications to process")
        return

    # Process notifications, oldest first
    new_notifs.sort(key=lambda x: x[1])
    latest_processed = last_indexed_at
    processed_count = 0

    for notif, indexed_at in new_notifs:
        txt = notif["record"]["text"].strip()
        uri = notif["uri"]
        reason = notif["reason"]

        print(f"\n📬 Processing notification: {indexed_at}")
        print(f"   Reason: {reason}")
        print(f"   Text: '{txt}'")
        print(f"   URI: {uri}")

        parent_text = await get_parent_post_text(uri, token)
        if parent_text:
            print(f"   Parent post text: '{parent_text}'")
            prompt = f"User replied to this message: '{parent_text}'. Their comment: '{txt}'. Provide a helpful response."
        else:
            prompt = f"User says: '{txt}'. Respond helpfully."

        print(f"   Prompt: '{prompt}'")

        reply = ask_local(prompt)
        print(f"   Generated reply: '{reply}'")

        await post_reply(reply, uri, token)
        print(f"✅ Replied: '{reply}'")

        processed_count += 1
        if indexed_at > latest_processed:
            latest_processed = indexed_at

        delay = random.randint(60, 120)
        print(f"⏳ Waiting {delay} seconds before next reply...")
        await asyncio.sleep(delay)

    # Save progress
    if latest_processed != last_indexed_at:
        save_last_processed(latest_processed)
        print(f"💾 Last processed time updated to: {latest_processed}")
    else:
        print("ℹ️ No new last processed time to save")

    # Reset UI counter
    await mark_notifications_as_read(token, latest_processed)
    print(f"✅ UI counter reset (marked up to {latest_processed})")

    print(f"🎉 Done: {processed_count} replies sent")

if __name__ == "__main__":
    asyncio.run(main())
