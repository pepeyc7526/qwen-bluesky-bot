#!/usr/bin/env python3
import os, json, datetime, asyncio, httpx, random
from llama_cpp import Llama

BOT_HANDLE = os.getenv("BOT_HANDLE")
BOT_PASSWORD = os.getenv("BOT_PASSWORD")
BOT_DID = os.getenv("BOT_DID")
OWNER_DID = os.getenv("OWNER_DID")
MAX_LEN = 300
SEARCH_USAGE_FILE = "search_usage.json"
LAST_PROCESSED_FILE = "last_processed.json"

if not all([BOT_HANDLE, BOT_PASSWORD, BOT_DID, OWNER_DID]):
    raise RuntimeError("Missing required env vars")

MODEL_PATH = "models/qwen2-7b-instruct-q4_k_m.gguf"
llm = Llama(model_path=MODEL_PATH, n_ctx=2048, n_threads=2, verbose=False)

# Кеши в /tmp для быстрого доступа
_TMP_LAST_PROCESSED = "/tmp/bot_last_processed"
_TMP_SEARCH_USAGE = "/tmp/bot_search_usage"

def load_last_processed():
    # Проверяем кеш в /tmp
    if os.path.exists(_TMP_LAST_PROCESSED):
        with open(_TMP_LAST_PROCESSED, "r") as f:
            return f.read().strip()
    
    # Читаем основной файл
    if os.path.exists(LAST_PROCESSED_FILE):
        with open(LAST_PROCESSED_FILE, "r") as f:
            data = json.load(f)
            result = data.get("indexedAt", "1970-01-01T00:00:00.000Z")
            with open(_TMP_LAST_PROCESSED, "w") as tmp:
                tmp.write(result)
            return result
    else:
        default = "1970-01-01T00:00:00.000Z"
        with open(_TMP_LAST_PROCESSED, "w") as tmp:
            tmp.write(default)
        return default

def save_last_processed(indexed_at):
    with open(LAST_PROCESSED_FILE, "w") as f:
        json.dump({"indexedAt": indexed_at}, f)
    with open(_TMP_LAST_PROCESSED, "w") as tmp:
        tmp.write(indexed_at)

def load_search_usage():
    if os.path.exists(_TMP_SEARCH_USAGE):
        with open(_TMP_SEARCH_USAGE, "r") as f:
            return json.loads(f.read())
    
    if os.path.exists(SEARCH_USAGE_FILE):
        with open(SEARCH_USAGE_FILE, "r") as f:
            result = json.load(f)
            with open(_TMP_SEARCH_USAGE, "w") as tmp:
                tmp.write(json.dumps(result))
            return result
    return {"count": 0, "month": datetime.datetime.now().month}

def save_search_usage(count: int):
    data = {"count": count, "month": datetime.datetime.now().month}
    with open(SEARCH_USAGE_FILE, "w") as f:
        json.dump(data, f)
    with open(_TMP_SEARCH_USAGE, "w") as tmp:
        tmp.write(json.dumps(data))

def should_reset_counter():
    usage = load_search_usage()
    current_month = datetime.datetime.now().month
    return usage["month"] != current_month

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
    except:
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
    except:
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
    except:
        return ""

def ask_local(prompt: str) -> str:
    prompt = prompt.replace(f"@{BOT_HANDLE}", "you")
    
    messages = [
        {"role": "system", "content": "You are a helpful AI assistant. Answer briefly and clearly. Keep under 300 chars. No links or emojis."},
        {"role": "user", "content": prompt}
    ]
    
    full_prompt = ""
    for msg in messages:
        if msg["role"] == "user":
            full_prompt += "<|im_start|>user\n" + msg['content'] + "<|im_end|>\n"
        elif msg["role"] == "assistant":
            full_prompt += "<|im_start|>assistant\n" + msg['content'] + "<|im_end|>\n"
        else:
            full_prompt += "<|im_start|>system\n" + msg['content'] + "<|im_end|>\n"
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

    if len(ans) <= MAX_LEN:
        return ans
    truncated = ans[:MAX_LEN].rsplit(' ', 1)[0]
    return truncated + "…" if truncated else ans[:MAX_LEN-1] + "…"

async def mark_notifications_as_read(token: str, seen_at: str, client):
    url = "https://bsky.social/xrpc/app.bsky.notification.updateSeen"
    payload = {"seenAt": seen_at}
    await client.post(url, headers={"Authorization": f"Bearer {token}"}, json=payload, timeout=30.0)

async def main():
    async with httpx.AsyncClient() as client:
        token = await get_fresh_token(client)

        if should_reset_counter():
            save_search_usage(0)

        last_indexed_at = load_last_processed()

        # Фильтрация через API параметры
        url = f"https://bsky.social/xrpc/app.bsky.notification.listNotifications?limit=50&seenAt={last_indexed_at}"
        r = await client.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=30.0)
        notifications = r.json().get("notifications", [])

        # Фильтрация по DID и типу уведомления сразу
        new_notifs = []
        for notif in notifications:
            indexed_at = notif.get("indexedAt", "")
            author_did = notif.get("author", {}).get("did", "")
            reason = notif.get("reason", "")
            record = notif.get("record", {})
            txt = record.get("text", "") if record else ""
            uri = notif.get("uri", "")

            if indexed_at <= last_indexed_at:
                continue
            if author_did != OWNER_DID:
                continue
            if reason not in ("mention", "reply"):
                continue
            if record.get("$type") != "app.bsky.feed.post":
                continue
            if not txt or not uri:
                continue

            new_notifs.append((notif, indexed_at))

        if not new_notifs:
            if notifications:
                latest = max(notifications, key=lambda x: x.get("indexedAt", ""))
                await mark_notifications_as_read(token, latest.get("indexedAt", ""), client)
            return

        new_notifs.sort(key=lambda x: x[1])
        latest_processed = last_indexed_at
        processed_count = 0

        for notif, indexed_at in new_notifs:
            txt = notif["record"]["text"]
            uri = notif["uri"]

            root_uri, root_cid = await get_root_uri_and_cid(uri, token, client)
            parent_uri = uri
            parent_cid = await get_cid(parent_uri, token, client)

            parent_text = await get_parent_post_text(uri, token, client)
            prompt = f"User replied to: '{parent_text}'. Comment: '{txt}'. Respond helpfully." if parent_text else f"User says: '{txt}'. Respond helpfully."
            reply = ask_local(prompt)
            await post_reply(reply, root_uri, root_cid, parent_uri, parent_cid, token, client)

            processed_count += 1
            if indexed_at > latest_processed:
                latest_processed = indexed_at

            await asyncio.sleep(random.randint(60, 120))

        if latest_processed != last_indexed_at:
            save_last_processed(latest_processed)

        final_seen_at = latest_processed if new_notifs else last_indexed_at
        await mark_notifications_as_read(token, final_seen_at, client)

if __name__ == "__main__":
    asyncio.run(main())
