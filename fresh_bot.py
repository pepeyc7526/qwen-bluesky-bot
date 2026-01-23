#!/usr/bin/env python3
import os, json, datetime, asyncio, httpx
from llama_cpp import Llama

BOT_HANDLE    = os.getenv("BOT_HANDLE", "bot-pepeyc7526.bsky.social")
BOT_PASSWORD  = os.getenv("BOT_PASSWORD")
BOT_DID       = "did:plc:er457dupy7iytuzdgfmfsuv7"
OWNER_DID     = "did:plc:topho472iindqxv5hm7nzww2"
MAX_LEN       = 300
SEARCH_USAGE_FILE = "search_usage.json"

MODEL_PATH = "models/qwen2-7b-instruct-q4_k_m.gguf"
llm = Llama(model_path=MODEL_PATH, n_ctx=2048, n_threads=2, verbose=False)

if not BOT_PASSWORD:
    raise RuntimeError("BOT_PASSWORD missing")

# === WEB SEARCH ===
async def web_search(query: str) -> str:
    api_key = os.getenv("GOOGLE_API_KEY")
    cse_id = os.getenv("GOOGLE_CSE_ID")
    if not api_key or not cse_id:
        return ""

    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": api_key,
        "cx": cse_id,
        "q": query,
        "num": 2
    }
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

# === BLUESKY FUNCTIONS ===
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
    messages = [
        {"role": "system", "content": "You are a helpful AI assistant. Use context if provided. Keep under 300 chars. No links or emojis."},
        {"role": "user", "content": prompt}
    ]
    
    full_prompt = ""
    for msg in messages:
        if msg["role"] == "user":
            full_prompt += f"<|im_start|>user\n{msg['content']}<|im_end|>>\n"
        elif msg["role"] == "assistant":
            full_prompt += f"<|im_start|>assistant\n{msg['content']}<|im_end|>>\n"
        else:
            full_prompt += f"<|im_start|>system\n{msg['content']}<|im_end|>>\n"
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

    if any(w in ans.lower() for w in ["don't know", "unclear", "provide more", "doesn't seem"]):
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

# === MAIN ===
async def main():
    token = await get_fresh_token()
    print("✅ Checking notifications...")

    # Reset counter if new month
    if should_reset_counter():
        save_search_usage(0)
        print("📅 Search counter reset")

    notifications = await get_notifications(token)
    print(f"📥 Found {len(notifications)} notifications")

    replied = False
    for notif in notifications:
        # Пропускаем, если уже прочитано
        if notif.get("isRead"):
            continue

        # Проверяем, что уведомление от тебя
        author_did = notif.get("author", {}).get("did", "")
        if author_did != OWNER_DID:
            continue

        # Проверяем тип
        if notif.get("reason") != "mention":
            continue

        record = notif.get("record", {})
        if record.get("$type") != "app.bsky.feed.post":
            continue

        txt = record.get("text", "")
        uri = notif.get("uri", "")

        if not uri:
            continue

        # Удаляем упоминание бота
        clean_txt = txt.strip()
        bot_mention = f"@{BOT_HANDLE}"
        if clean_txt.startswith(bot_mention):
            clean_txt = clean_txt[len(bot_mention):].strip()

        print(f"🔍 Cleaned text: '{clean_txt}'")

        # === ai web ... ===
        if clean_txt.lower().startswith("ai web "):
            content = clean_txt[7:].strip()
            if content:
                usage = load_search_usage()
                if usage["count"] >= 100:
                    reply = "🔍 Web search limit reached (100/month). Try again next month!"
                else:
                    print(f"🌐 Web search ({usage['count']+1}/100): {content}")
                    context = await web_search(content)
                    prompt = f"Context: {context}\nQuestion: {content}" if context else f"Question: {content}"
                    reply = ask_local(prompt)
                    save_search_usage(usage["count"] + 1)
                await post_reply(reply, uri, token)
                print(f"✅ Replied (web) to {uri}")
                replied = True

        # === ai ... ===
        elif clean_txt.lower().startswith("ai "):
            content = clean_txt[3:].strip()
            if content:
                reply = ask_local(f"Question: {content}")
                await post_reply(reply, uri, token)
                print(f"✅ Replied (local) to {uri}")
                replied = True

        if replied:
            break

    # Помечаем всё как прочитанное
    seen_at = datetime.datetime.utcnow().isoformat() + "Z"
    await mark_as_read(token, seen_at)
    print("✅ All notifications marked as read")

if __name__ == "__main__":
    asyncio.run(main())
