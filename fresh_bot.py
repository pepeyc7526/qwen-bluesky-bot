#!/usr/bin/env python3
import os, json, datetime, asyncio, httpx, random
from llama_cpp import Llama

# Load all config from environment variables
BOT_HANDLE    = os.getenv("BOT_HANDLE")
BOT_PASSWORD  = os.getenv("BOT_PASSWORD")
BOT_DID       = os.getenv("BOT_DID")
OWNER_DID     = os.getenv("OWNER_DID")
MAX_LEN       = 300
SEARCH_USAGE_FILE = "search_usage.json"
PROCESSED_NOTIF_KEYS_FILE = "processed_notif_keys.json"

# Validate required environment variables
if not all([BOT_HANDLE, BOT_PASSWORD, BOT_DID, OWNER_DID]):
    raise RuntimeError("Missing required env vars: BOT_HANDLE, BOT_PASSWORD, BOT_DID, OWNER_DID")

MODEL_PATH = "models/qwen2-7b-instruct-q4_k_m.gguf"
llm = Llama(model_path=MODEL_PATH, n_ctx=2048, n_threads=2, verbose=False)

def load_processed_notif_keys():
    if os.path.exists(PROCESSED_NOTIF_KEYS_FILE):
        with open(PROCESSED_NOTIF_KEYS_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_processed_notif_keys(keys):
    with open(PROCESSED_NOTIF_KEYS_FILE, "w") as f:
        json.dump(list(keys), f)

# === WEB SEARCH ===
async def web_search(query: str) -> str:
    api_key = os.getenv("GOOGLE_API_KEY")
    cse_id = os.getenv("GOOGLE_CSE_ID")
    if not api_key or not cse_id:
        return ""
    url = "https://www.googleapis.com/customsearch/v1"
    params = {"key": api_key, "cx": cse_id, "q": query, "num": 2}
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(url, params=params, timeout=10.0)
            data = r.json()
            results = data.get("items", [])
            snippets = [f"{item['title']}: {item['snippet']}" for item in results]
            return " | ".join(snippets[:2])
        except Exception as e:
            print(f"[SEARCH ERROR] {e}")
            return ""

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

# === BLUESKY AUTHENTICATION ===
async def get_fresh_token() -> str:
    url = "https://bsky.social/xrpc/com.atproto.server.createSession"
    payload = {"identifier": BOT_HANDLE, "password": BOT_PASSWORD}
    async with httpx.AsyncClient() as client:
        r = await client.post(url, json=payload)
        return r.json()["accessJwt"]

# === POSTING FUNCTIONS ===
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

# === NOTIFICATIONS ===
async def get_notifications(token: str):
    url = "https://bsky.social/xrpc/app.bsky.notification.listNotifications"
    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers={"Authorization": f"Bearer {token}"})
        return r.json().get("notifications", [])

# === CONTEXT AWARENESS ===
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

# === AI RESPONSE GENERATION ===
def ask_local(prompt: str) -> str:
    messages = [
        {"role": "system", "content": "You are a helpful AI assistant. Answer briefly and clearly. Keep under 300 chars. No links or emojis."},
        {"role": "user", "content": prompt}
    ]
    
    full_prompt = ""
    for msg in messages:
        if msg["role"] == "user":
            full_prompt += f"                              <|im_start|>user\n{msg['content']}<|im_end|>>\n"
        elif msg["role"] == "assistant":
            full_prompt += f"                              <|im_start|>assistant\n{msg['content']}<|im_end|>>\n"
        else:
            full_prompt += f"                              <|im_start|>system\n{msg['content']}<|im_end|>>\n"
    full_prompt += "                              <|im_start|>assistant\n"

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

# === REPLY POSTING ===
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

# === MAIN LOGIC ===
async def main():
    token = await get_fresh_token()
    print("✅ Checking notifications...")

    if should_reset_counter():
        save_search_usage(0)
        print("📅 Search counter reset")

    processed_keys = load_processed_notif_keys()
    new_processed = set(processed_keys)
    print(f"💾 Loaded {len(processed_keys)} processed notification keys")

    notifications = await get_notifications(token)
    print(f"📥 Found {len(notifications)} notifications")

    valid_notifs = []
    for notif in notifications:
        indexed_at = notif.get("indexedAt")
        author_did = notif.get("author", {}).get("did", "")
        reason = notif.get("reason")
        record = notif.get("record", {})
        txt = record.get("text", "") if record else ""
        txt_preview = txt[:60].replace('\n', ' ') if txt else ''

        print(f"\n📨 Notification indexedAt: {indexed_at or 'N/A'}")
        print(f"   Author DID: {author_did}")
        print(f"   Reason: {reason}")
        print(f"   Text preview: '{txt_preview}...'")

        # Skip if not from owner
        if author_did != OWNER_DID:
            print("   ❌ Skipped: not from owner")
            continue

        # Skip if not mention or reply
        if reason not in ("mention", "reply"):
            print("   ❌ Skipped: not mention or reply")
            continue

        # Skip if not a post
        if record.get("$type") != "app.bsky.feed.post":
            print("   ❌ Skipped: not a post")
            continue

        # Skip if no indexedAt
        if not indexed_at:
            print("   ❌ Skipped: no indexedAt")
            continue

        # Skip if already processed
        if indexed_at in processed_keys:
            print("   ❌ Skipped: already processed")
            continue

        valid_notifs.append((notif, indexed_at))

    # Process oldest first
    valid_notifs.sort(key=lambda x: x[0].get("indexedAt", ""))

    for notif, indexed_at in valid_notifs:
        txt = notif.get("text", "")
        uri = notif.get("uri", "")
        reason = notif.get("reason")

        # For 'mention', always process — handle may be normalized out by API
        if reason == "mention":
            clean_txt = txt.strip()
            # If empty after strip, skip
            if not clean_txt:
                print("   ❌ Skipped: empty mention text")
                continue
        else:
            # For 'reply', clean bot mention if present
            clean_txt = txt.strip()
            bot_mention = f"@{BOT_HANDLE}"
            if bot_mention in clean_txt:
                clean_txt = clean_txt.replace(bot_mention, "", 1).strip()
            # Allow empty reply? No — skip if empty
            if not clean_txt:
                print("   ❌ Skipped: empty reply text")
                continue

        print(f"🔍 Cleaned text: '{clean_txt}'")

        parent_text = await get_parent_post_text(uri, token)
        if parent_text:
            prompt = f"User replied to this message: '{parent_text}'. Their comment: '{clean_txt}'. Provide a helpful response."
        else:
            prompt = f"User says: '{clean_txt}'. Respond helpfully."

        reply = ask_local(prompt)
        await post_reply(reply, uri, token)
        print(f"✅ Replied to {uri}")

        new_processed.add(indexed_at)

        delay = random.randint(60, 120)
        print(f"⏳ Waiting {delay} seconds before next reply...")
        await asyncio.sleep(delay)

    if new_processed != processed_keys:
        save_processed_notif_keys(new_processed)
        print(f"\n💾 Saved {len(new_processed)} processed notification keys")
    else:
        print("\nℹ️ No new notifications to process")

    seen_at = datetime.datetime.utcnow().isoformat() + "Z"
    async with httpx.AsyncClient() as client:
        await client.post(
            "https://bsky.social/xrpc/app.bsky.notification.updateSeen",
            headers={"Authorization": f"Bearer {token}"},
            json={"seenAt": seen_at}
        )
    print("✅ All notifications marked as read")

if __name__ == "__main__":
    asyncio.run(main())
