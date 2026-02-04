#!/usr/bin/env python3
import os, json, datetime, asyncio, httpx, random
from llama_cpp import Llama
from base64 import b64encode
from nacl import encoding, public

BOT_HANDLE = os.getenv("BOT_HANDLE")
BOT_PASSWORD = os.getenv("BOT_PASSWORD")
BOT_DID = os.getenv("BOT_DID")
OWNER_DID = os.getenv("OWNER_DID")
MAX_LEN = 300

if not all([BOT_HANDLE, BOT_PASSWORD, BOT_DID, OWNER_DID]):
    raise RuntimeError("Missing required env vars: BOT_HANDLE, BOT_PASSWORD, BOT_DID, OWNER_DID")

MODEL_PATH = "models/qwen2-7b-instruct-q4_k_m.gguf"
llm = Llama(model_path=MODEL_PATH, n_ctx=2048, n_threads=2, verbose=False)

# === GITHUB SECRETS ENCRYPTION ===
def encrypt_secret(public_key: str, secret_value: str) -> str:
    public_key = public.PublicKey(public_key.encode("utf-8"), encoding.Base64Encoder())
    sealed_box = public.SealedBox(public_key)
    encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
    return b64encode(encrypted).decode("utf-8")

async def get_repo_public_key():
    repo = os.getenv("GITHUB_REPOSITORY")
    token = os.getenv("GITHUB_TOKEN")
    url = f"https://api.github.com/repos/{repo}/actions/secrets/public-key"
    headers = {"Authorization": f"token {token}"}
    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers=headers)
        return r.json()

async def save_state_encrypted(state):
    try:
        key_data = await get_repo_public_key()
        encrypted = encrypt_secret(key_data["key"], json.dumps(state))
        repo = os.getenv("GITHUB_REPOSITORY")
        token = os.getenv("GITHUB_TOKEN")
        url = f"https://api.github.com/repos/{repo}/actions/secrets/BOT_STATE"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
        payload = {
            "encrypted_value": encrypted,
            "key_id": key_data["key_id"]
        }
        async with httpx.AsyncClient() as client:
            r = await client.put(url, headers=headers, json=payload)
            if r.status_code in (201, 204):
                print("✅ State saved to secret")
            else:
                print(f"[SAVE ERROR] {r.status_code}: {r.text}")
    except Exception as e:
        print(f"[SAVE EXCEPTION] {e}")

def load_state():
    try:
        state_str = os.getenv("BOT_STATE", "{}")
        return json.loads(state_str)
    except Exception as e:
        print(f"[STATE LOAD ERROR] {e}")
        return {}

def is_duplicate_reply(new_reply, recent_replies):
    new_clean = new_reply.strip().lower()
    for reply in recent_replies:
        if new_clean == reply.strip().lower():
            return True
    return False

# === LIVE DATA APIS ===
async def get_bitcoin_price():
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", timeout=5.0)
            price = r.json()["bitcoin"]["usd"]
            return f"Current Bitcoin price: ${price:,}"
    except:
        return "⚠️ Bitcoin price unavailable."

async def get_weather(city):
    coords = {
        "london": (51.5074, -0.1278),
        "tokyo": (35.6895, 139.6917),
        "new york": (40.7128, -74.0060),
        "paris": (48.8566, 2.3522),
        "berlin": (52.5200, 13.4050),
        "moscow": (55.7558, 37.6173)
    }
    city_lower = city.lower()
    if city_lower not in coords:
        return "⚠️ Weather available for: London, Tokyo, New York, Paris, Berlin, Moscow."
    
    lat, lon = coords[city_lower]
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m"
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(url, timeout=5.0)
            temp = r.json()["current"]["temperature_2m"]
            return f"Current temperature in {city.title()}: {temp}°C"
    except:
        return "⚠️ Weather service unavailable."

async def get_time(location):
    tz_map = {
        "london": "Europe/London",
        "tokyo": "Asia/Tokyo",
        "new york": "America/New_York",
        "paris": "Europe/Paris",
        "berlin": "Europe/Berlin",
        "moscow": "Europe/Moscow"
    }
    loc_lower = location.lower()
    if loc_lower not in tz_map:
        return "⚠️ Time available for: London, Tokyo, New York, Paris, Berlin, Moscow."
    
    tz = tz_map[loc_lower]
    url = f"http://worldtimeapi.org/api/timezone/{tz}"
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(url, timeout=5.0)
            time_str = r.json()["datetime"].split("T")[1][:5]
            return f"Current time in {location.title()}: {time_str}"
    except:
        return "⚠️ Time service unavailable."

# === MAIN LOGIC ===
async def ask_local(prompt: str) -> str:
    prompt = prompt.replace(f"@{BOT_HANDLE}", "you")
    
    # === WEB SEARCH DETECTION ===
    web_query = None
    prompt_clean = prompt.strip()
    if prompt_clean.lower().startswith("'web'"):
        web_query = prompt_clean[6:].strip()
    elif " 'web' " in prompt_clean.lower():
        parts = prompt_clean.split("'web'", 1)
        if len(parts) == 2:
            web_query = parts[1].strip()
    
    if web_query:
        query_lower = web_query.lower()
        
        # BITCOIN PRICE
        if "bitcoin" in query_lower and "price" in query_lower:
            return await get_bitcoin_price()
        
        # WEATHER
        if "weather" in query_lower or "temperature" in query_lower:
            for city in ["london", "tokyo", "new york", "paris", "berlin", "moscow"]:
                if city in query_lower:
                    return await get_weather(city)
            return "⚠️ Specify a city: 'web weather in London'"
        
        # TIME
        if "time" in query_lower:
            for loc in ["london", "tokyo", "new york", "paris", "berlin", "moscow"]:
                if loc in query_lower:
                    return await get_time(loc)
            return "⚠️ Specify location: 'web time in Tokyo'"
        
        # FACTUAL QUERIES (DuckDuckGo)
        try:
            from urllib.parse import quote_plus
            query = quote_plus(web_query)
            url = f"https://api.duckduckgo.com/?q={query}&format=json&no_html=1&skip_disambig=1"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=10.0)
                data = response.json()
                
                answer = data.get("AbstractText", "").strip()
                if not answer:
                    related = data.get("RelatedTopics", [])
                    if related and isinstance(related[0], dict):
                        answer = related[0].get("Text", "").strip()
                
                if answer:
                    if len(answer) > MAX_LEN:
                        answer = answer[:MAX_LEN].rsplit(' ', 1)[0] + "…"
                    return answer
            
            return "🌐 No clear answer found."
            
        except Exception as e:
            print(f"[DUCKDUCKGO ERROR] {e}")
            return "⚠️ Search failed. Try again later."

    # === REGULAR MODE ===
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

# === BLUESKY FUNCTIONS (unchanged) ===
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

async def mark_notifications_as_read(token: str, seen_at: str, client):
    url = "https://bsky.social/xrpc/app.bsky.notification.updateSeen"
    payload = {"seenAt": seen_at}
    await client.post(url, headers={"Authorization": f"Bearer {token}"}, json=payload, timeout=30.0)

# === MAIN ===
async def main():
    async with httpx.AsyncClient() as client:
        token = await get_fresh_token(client)
        print("✅ Starting bot...")

        state = load_state()
        last_indexed_at = state.get("last_processed", "1970-01-01T00:00:00.000Z")
        recent_replies = state.get("recent_replies", [])

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

            reply = await ask_local(prompt)
            if is_duplicate_reply(reply, recent_replies):
                print("[DUPLICATE] Generating fallback response...")
                fallback_prompt = "Give a completely different response."
                reply = await ask_local(fallback_prompt)

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

        state["last_processed"] = latest_processed
        state["recent_replies"] = recent_replies

        await save_state_encrypted(state)
        print(f"🎉 Done: {processed_count} replies sent")

if __name__ == "__main__":
    asyncio.run(main())
