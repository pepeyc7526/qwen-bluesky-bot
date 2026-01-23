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
    print("🔑 Requesting fresh session token...")
    url = "https://bsky.social/xrpc/com.atproto.server.createSession"
    payload = {"identifier": BOT_HANDLE, "password": BOT_PASSWORD}
    async with httpx.AsyncClient() as client:
        r = await client.post(url, json=payload, timeout=10.0)
        r.raise_for_status()
        data = r.json()
        print("✅ Got fresh access token")
        return data["accessJwt"]

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
        r = await client.post(
            url,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=payload,
        )
        print(f"📤 Post response: {r.status_code}")
        if r.status_code != 200:
            print(f"❌ Error: {r.text}")
        else:
            print(f"✅ Post URI: {r.json().get('uri')}")

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

async def bluesky_stream(token: str):
    print("📡 Connecting to Bluesky event stream...")
    url = "https://bsky.social/xrpc/com.atproto.sync.subscribeRepos"
    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream("GET", url, headers={"Authorization": f"Bearer {token}"}) as resp:
            async for line in resp.aiter_lines():
                if not line.strip(): continue
                try: ev = json.loads(line)
                except: continue
                if ev.get("$type") != "com.atproto.sync.subscribeRepos#commit": continue
                for op in ev.get("ops", []):
                    if op.get("action") != "create" or "post" not in op.get("path", ""): continue
                    rec = op.get("payload", {})
                    if rec.get("$type") != "app.bsky.feed.post": continue
                    txt = rec.get("text", "")
                    uri = rec.get("uri", "")
                    author_did = ev.get("repo", "")

                    reply_to_uri = None
                    if "reply" in rec and "parent" in rec["reply"]:
                        reply_to_uri = rec["reply"]["parent"]["uri"]

                    mentioned = f"@{BOT_HANDLE}" in txt.lower()
                    from_owner = (author_did == OWNER_DID)
                    if not (mentioned or from_owner): continue
                    if not txt.lower().strip().startswith("ai"): continue

                    yield txt, uri, author_did, reply_to_uri

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
        await client.post(
            url,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=payload,
        )

async def main():
    token = await get_fresh_token()
    print("✅ Bot started. Posting startup message...")
    await post_to_bluesky("✅ Bot started", token)
    print("👂 Listening for 'ai' mentions or commands from owner...")
    async for txt, uri, author_did, reply_to_uri in bluesky_stream(token):
        print(f"📬 Received: {txt[:50]}...")
        try:
            if reply_to_uri:
                parent_text = await get_post_text(reply_to_uri, token)
                prompt = f"Parent: {parent_text}\nComment: {txt}"
            else:
                content = txt[len("ai"):].strip()
                prompt = f"User request: {content}"

            reply = ask_local(prompt)
            await post_reply(reply, uri, token)
            await post_to_bluesky("📨 Processed an 'ai' request", token)
            print(f"✅ Replied to {uri}")
        except Exception as e:
            print(f"[ERROR] {e}")

if __name__ == "__main__":
    asyncio.run(main())
