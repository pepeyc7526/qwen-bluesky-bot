#!/usr/bin/env python3
import os, json, datetime, asyncio, httpx, random
from llama_cpp import Llama

# === GitHub Secrets ===
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # Must be set to your PAT with repo scope
REPO = os.getenv("GITHUB_REPOSITORY")
STATE_SECRET_NAME = "BOT_STATE"

BOT_HANDLE = os.getenv("BOT_HANDLE")
BOT_PASSWORD = os.getenv("BOT_PASSWORD")
BOT_DID = os.getenv("BOT_DID")
OWNER_DID = os.getenv("OWNER_DID")
MAX_LEN = 300

if not all([BOT_HANDLE, BOT_PASSWORD, BOT_DID, OWNER_DID, GITHUB_TOKEN, REPO]):
    raise RuntimeError("Missing required env vars: BOT_HANDLE, BOT_PASSWORD, BOT_DID, OWNER_DID, GITHUB_TOKEN, GITHUB_REPOSITORY")

MODEL_PATH = "models/qwen2-7b-instruct-q4_k_m.gguf"
llm = Llama(model_path=MODEL_PATH, n_ctx=2048, n_threads=2, verbose=False)

# === State management via GitHub Secrets ===
async def load_state():
    """Load state from GitHub secret"""
    try:
        url = f"https://api.github.com/repos/{REPO}/actions/secrets/{STATE_SECRET_NAME}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        async with httpx.AsyncClient() as client:
            r = await client.get(url, headers=headers)
            if r.status_code == 404:
                print("ℹ️ No state found — starting fresh")
                return {}
            value = r.json().get("value", "{}")
            state = json.loads(value)
            print(f"✅ Loaded state:")
            print(f"   Last processed: {state.get('last_processed', 'N/A')}")
            print(f"   Recent replies count: {len(state.get('recent_replies', []))}")
            print(f"   Search usage: {state.get('search_usage', {}).get('count', 'N/A')}")
            return state
    except Exception as e:
        print(f"[STATE LOAD ERROR] {e}")
        return {}

async def save_state(state):
    """Save state to GitHub secret"""
    try:
        url = f"https://api.github.com/repos/{REPO}/actions/secrets/{STATE_SECRET_NAME}"
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        payload = {"value": json.dumps(state)}
        async with httpx.AsyncClient() as client:
            r = await client.patch(url, headers=headers, json=payload)
            if r.status_code in (200, 204):
                print(f"✅ State saved successfully")
                print(f"   Last processed: {state.get('last_processed', 'N/A')}")
                print(f"   Recent replies count: {len(state.get('recent_replies', []))}")
                print(f"   Search usage: {state.get('search_usage', {}).get('count', 'N/A')}")
            else:
                print(f"[STATE SAVE ERROR] Status: {r.status_code}, Response: {r.text}")
    except Exception as e:
        print(f"[STATE SAVE EXCEPTION] {e}")

def get_last_processed(state):
    return state.get("last_processed", "1970-01-01T00:00:00.000Z")

def get_recent_replies(state):
    return state.get("recent_replies", [])

def get_search_usage(state):
    return state.get("search_usage", {"count": 0, "month": datetime.datetime.now().month})

def should_reset_counter(usage):
    return usage["month"] != datetime.datetime.now().month

def is_duplicate_reply(new_reply, recent_replies):
    new_clean = new_reply.strip().lower()
    for reply in recent_replies:
        if new_clean == reply.strip().lower():
            return True
    return False

# === Bluesky API functions ===
async def get_fresh_token(client) -> str:
    url = "https://bsky.social/xrpc/com.atproto.server.createSession"
    payload = {"identifier": BOT_HANDLE, "password": BOT_PASSWORD}
    r = await client.post(url, json=payload, timeout=30.0)
    return r.json()["accessJwt"]

async def get_cid(uri: str, token: str, client) -> str:
    try:
        parts = uri.split("/")
        repo, collection, rkey = parts[2], parts[3], parts[4]
        url = f"https://bsky.social/xrpc/com.atproto.repo.getRecord?repo={repo}&collection={collection}&rkey={rkey}"
        r = await client.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=30.0)
        return r.json().get("cid", "bafyreihjdbd4zq4f4a5v6w5z5g5q5j5j5j5j5j5j5j5j5j5j5j5j5j5j5j5j5j")
    except Exception as e:
        print(f"[CID ERROR] {e}")
        return "bafyreihjdbd4zq4f4a5v6w5z5g5q5j5j5j5j5j5j5j5j5j5j5j5j5j5j5j5j5j"

async def post_reply(text: str, root_uri: str, root_cid: str, parent_uri: str, parent_cid: str, token: str, client):
    url = "https://bsky.social/xrpc/com.atproto.repo.createRecord"
    payload = {
        "repo": BOT_DID,
        "collection": "app.bsky.feed.post",
        "record": {
            "$type": "app.bsky.feed.post",
            "text": text,
            "reply": {
                "root": {"uri": root_uri, "cid": root_cid},
                "parent": {"uri": parent_uri, "cid": parent_cid}
            },
            "createdAt": datetime.datetime.utcnow().isoformat() + "Z"
        }
    }
    await client.post(url, headers={"Authorization": f"Bearer {token}"}, json=payload, timeout=30.0)

async def get_root_uri_and_cid(uri: str, token: str, client):
    try:
        parts = uri.split("/")
        repo, rkey = parts[2], parts[4]
        url = f"https://bsky.social/xrpc/com.atproto.repo.getRecord?repo={repo}&collection=app.bsky.feed.post&rkey={rkey}"
        r = await client.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=30.0)
        record = r.json().get("value", {})
        reply = record.get("reply")
        
        if not reply or "root" not in reply:
            return uri, record.get("cid", "bafyreihjdbd4zq4f4a5v6w5z5g5q5j5j5j5j5j5j5j5j5j5j5j5j5j5j5j5j5j")
        
        root_uri = reply["root"]["uri"]
        root_parts = root_uri.split("/")
        root_repo, root_rkey = root_parts[2], root_parts[4]
        root_url = f"https://bsky.social/xrpc/com.atproto.repo.getRecord?repo={root_repo}&collection=app.bsky.feed.post&rkey={root_rkey}"
        r_root = await client.get(root_url, headers={"Authorization": f"Bearer {token}"}, timeout=30.0)
        root_cid = r_root.json().get("cid", "bafyreihjdbd4zq4f4a5v6w5z5g5q5j5j5j5j5j5j5j5j5j5j5j5j5j5j5j5j5j")
        
        return root_uri, root_cid
    except Exception as e:
        print(f"[ROOT EXTRACTION ERROR] {e}")
        fallback_cid = "bafyreihjdbd4zq4f4a5v6w5z5g5q5j5j5j5j5j5j5j5j5j5j5j5j5j5j5j5j5j"
        return uri, fallback_cid

async def get_parent_post_text(uri: str, token: str, client) -> str:
    try:
        parts = uri.split("/")
        repo, rkey = parts[2], parts[4]
        url = f"https://bsky.social/xrpc/com.atproto.repo.getRecord?repo={repo}&collection=app.bsky.feed.post&rkey={rkey}"
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
        print(f"[PARENT TEXT ERROR] {e}")
        return ""

def ask_local(prompt: str) -> str:
    prompt = prompt.replace(f"@{BOT_HANDLE}", "you")
    
    messages = [
        {"role": "system", "content": "You are a helpful AI assistant. Answer briefly and clearly. Keep under 300 chars. No links or emojis. NEVER repeat the same information twice."},
        {"role": "user", "content": prompt}
    ]
    
    full_prompt = ""
    for msg in messages:
        if msg["role"] == "user":
            full_prompt += "  user\n" + msg['content'] + "  \n"
        elif msg["role"] == "assistant":
            full_prompt += "  assistant\n" + msg['content'] + "  \n"
        else:
            full_prompt += "  system\n" + msg['content'] + "  \n"
    full_prompt += "  assistant\n"

    out = llm(
        full_prompt,
        max_tokens=120,
        stop=["  ", "  "],
        echo=False,
        temperature=0.3
    )
    ans = out["choices"][0]["text"].strip()
    ans = " ".join(ans.split())

    if any(w in ans.lower() for w in ["don't know", "unclear", "provide more", "doesn't seem"]):
        ans = "🤔 Not sure what you mean. Try rephrasing!"

    if len(ans) <= MAX_LEN:
        return ans
    truncated = ans[:MAX_LEN].rsplit(' ', 1)[0]
    return truncated + "…" if truncated else ans[:MAX_LEN-1] + "…"

async def mark_notifications_as_read(token: str, seen_at: str, client):
    url = "https://bsky.social/xrpc/app.bsky.notification.updateSeen"
    payload = {"seenAt": seen_at}
    await client.post(url, headers={"Authorization": f"Bearer {token}"}, json=payload, timeout=30.0)

# === MAIN ===
async def main():
    async with httpx.AsyncClient() as client:
        token = await get_fresh_token(client)
        print("✅ Starting bot...")

        # Load full state
        state = await load_state()
        last_indexed_at = get_last_processed(state)
        recent_replies = get_recent_replies(state)
        search_usage = get_search_usage(state)

        if should_reset_counter(search_usage):
            search_usage = {"count": 0, "month": datetime.datetime.now().month}

        url = "https://bsky.social/xrpc/app.bsky.notification.listNotifications"
        r = await client.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=30.0)
        notifications = r.json().get("notifications", [])
        print(f"📥 Found {len(notifications)} notifications")

        new_notifs = []
        for notif in notifications:
            indexed_at = notif.get("indexedAt", "")
            author_did = notif.get("author", {}).get("did", "")
            reason = notif.get("reason", "")
            record = notif.get("record", {})
            txt = record.get("text", "").strip() if record else ""
            uri = notif.get("uri", "")

            if not indexed_at or not txt or not uri:
                continue
            if indexed_at <= last_indexed_at:
                continue
            if author_did != OWNER_DID:
                continue
            if reason not in ("mention", "reply"):
                continue
            if record.get("$type") != "app.bsky.feed.post":
                continue

            should_process = False
            if reason == "mention":
                should_process = True
            elif reason == "reply":
                reply = record.get("reply", {})
                parent_uri = reply.get("parent", {}).get("uri", "")
                if parent_uri:
                    try:
                        parent_did = parent_uri.split("/")[2]
                        if parent_did == BOT_DID:
                            should_process = True
                    except:
                        pass

            if should_process:
                new_notifs.append((notif, indexed_at))

        if not new_notifs:
            if notifications:
                latest = max(notifications, key=lambda x: x.get("indexedAt", ""))
                await mark_notifications_as_read(token, latest.get("indexedAt", ""), client)
                print(f"✅ UI counter reset (marked up to {latest.get('indexedAt')})")
            else:
                print("ℹ️ No notifications to process")
            return

        new_notifs.sort(key=lambda x: x[1])
        latest_processed = last_indexed_at
        processed_count = 0

        for notif, indexed_at in new_notifs:
            txt = notif["record"]["text"].strip()
            uri = notif["uri"]
            reason = notif["reason"]

            print(f"\n📬 Processing: {indexed_at} | {reason} | '{txt[:50]}...'")

            root_uri, root_cid = await get_root_uri_and_cid(uri, token, client)
            parent_uri = uri
            parent_cid = await get_cid(parent_uri, token, client)

            print(f"🔗 Replying to user's comment: parent={parent_uri.split('/')[-1]}, root={root_uri.split('/')[-1]}")

            parent_text = await get_parent_post_text(uri, token, client)
            prompt = f"User says: '{txt}'. Respond helpfully."
            if parent_text:
                prompt = f"User replied to: '{parent_text}'. Comment: '{txt}'. Respond helpfully."

            reply = ask_local(prompt)
            if is_duplicate_reply(reply, recent_replies):
                print("[DUPLICATE] Generating fallback response...")
                fallback_prompt = "Give a completely different response."
                reply = ask_local(fallback_prompt)

            recent_replies.append(reply)
            if len(recent_replies) > 100:
                recent_replies = recent_replies[-100:]

            await post_reply(reply, root_uri, root_cid, parent_uri, parent_cid, token, client)
            print(f"✅ Replied: '{reply}'")

            processed_count += 1
            if indexed_at > latest_processed:
                latest_processed = indexed_at

            delay = random.randint(60, 120)
            print(f"⏳ Waiting {delay} seconds...")
            await asyncio.sleep(delay)

        # Update state
        state["last_processed"] = latest_processed
        state["recent_replies"] = recent_replies
        state["search_usage"] = search_usage

        await save_state(state)
        print(f"🎉 Done: {processed_count} replies sent")

if __name__ == "__main__":
    asyncio.run(main())
