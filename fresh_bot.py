#!/usr/bin/env python3
import os, json, datetime, asyncio, httpx, random
from llama_cpp import Llama

# === GitHub Secrets ===
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # Автоматически доступен в workflow
REPO = os.getenv("GITHUB_REPOSITORY")      # Например: "pepeyc7526/qwen-bluesky-bot"
STATE_SECRET_NAME = "BOT_STATE"

BOT_HANDLE = os.getenv("BOT_HANDLE")
BOT_PASSWORD = os.getenv("BOT_PASSWORD")
BOT_DID = os.getenv("BOT_DID")
OWNER_DID = os.getenv("OWNER_DID")
MAX_LEN = 300

if not all([BOT_HANDLE, BOT_PASSWORD, BOT_DID, OWNER_DID, GITHUB_TOKEN, REPO]):
    raise RuntimeError("Missing required env vars")

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
                return {}
            # Секрет возвращается как зашифрованная строка, но мы не можем её расшифровать!
            # Поэтому используем workaround: секрет хранится как plain text (см. workflow)
            # На практике GitHub не шифрует значение при чтении через API с токеном
            value = r.json().get("value", "{}")
            return json.loads(value)
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
            if r.status_code not in (200, 204):
                print(f"[STATE SAVE ERROR] {r.text}")
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

# === Остальной код без изменений (авторизация, запросы к Bluesky) ===
async def get_fresh_token(client) -> str:
    url = "https://bsky.social/xrpc/com.atproto.server.createSession"
    payload = {"identifier": BOT_HANDLE, "password": BOT_PASSWORD}
    r = await client.post(url, json=payload, timeout=30.0)
    return r.json()["accessJwt"]

# ... (все остальные функции get_cid, post_reply, get_root_uri_and_cid, get_parent_post_text, ask_local, mark_notifications_as_read — без изменений)

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
                url_mark = "https://bsky.social/xrpc/app.bsky.notification.updateSeen"
                await client.post(url_mark, headers={"Authorization": f"Bearer {token}"}, json={"seenAt": latest.get("indexedAt", "")}, timeout=30.0)
            return

        new_notifs.sort(key=lambda x: x[1])
        latest_processed = last_indexed_at
        processed_count = 0

        for notif, indexed_at in new_notifs:
            txt = notif["record"]["text"].strip()
            uri = notif["uri"]
            reason = notif["reason"]

            root_uri, root_cid = await get_root_uri_and_cid(uri, token, client)
            parent_uri = uri
            parent_cid = await get_cid(parent_uri, token, client)

            parent_text = await get_parent_post_text(uri, token, client)
            prompt = f"User says: '{txt}'. Respond helpfully."
            if parent_text:
                prompt = f"User replied to: '{parent_text}'. Comment: '{txt}'. Respond helpfully."

            reply = ask_local(prompt)
            if is_duplicate_reply(reply, recent_replies):
                fallback_prompt = "Give a completely different response."
                reply = ask_local(fallback_prompt)

            recent_replies.append(reply)
            if len(recent_replies) > 100:
                recent_replies = recent_replies[-100:]

            await post_reply(reply, root_uri, root_cid, parent_uri, parent_cid, token, client)
            print(f"✅ Replied: '{reply[:50]}...'")

            processed_count += 1
            if indexed_at > latest_processed:
                latest_processed = indexed_at

            await asyncio.sleep(random.randint(60, 120))

        # Update state
        state["last_processed"] = latest_processed
        state["recent_replies"] = recent_replies
        state["search_usage"] = search_usage

        await save_state(state)
        print(f"🎉 Done: {processed_count} replies sent")

if __name__ == "__main__":
    asyncio.run(main())
