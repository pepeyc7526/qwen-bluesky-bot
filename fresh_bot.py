#!/usr/bin/env python3
import os, json, datetime, asyncio, httpx
from llama_cpp import Llama

# ---------- CONFIG ----------
BLUESKY_TOKEN = os.getenv("BLUESKY_TOKEN")
BOT_HANDLE    = "bot-pepeyc7526.bsky.social"
OWNER_DID     = "did:plc:topho472iindqxv5hm7nzww2"
MAX_LEN       = 300
ELLIPSIS      = "…"

MODEL_PATH = "models/Phi-3-mini-4k-instruct-q4.gguf"
llm = Llama(model_path=MODEL_PATH, n_ctx=2048, n_threads=2, verbose=False)
# --------------------------

if not BLUESKY_TOKEN:
    raise RuntimeError("BLUESKY_TOKEN missing")

async def post_to_bluesky(text: str):
    """Post a standalone message from the bot."""
    url = "https://bsky.social/xrpc/com.atproto.repo.createRecord"
    payload = {
        "$type": "app.bsky.feed.post",
        "text": text,
        "createdAt": datetime.datetime.utcnow().isoformat() + "Z"
    }
    async with httpx.AsyncClient() as client:
        await client.post(
            url,
            headers={
                "Authorization": f"Bearer {BLUESKY_TOKEN}",
                "Content-Type": "application/json"
            },
            json=payload,
        )

async def get_record_cid(uri: str):
    try:
        parts = uri.split("/")
        repo, collection, rkey = parts[2], parts[3], parts[4]
        url = f"https://bsky.social/xrpc/com.atproto.repo.getRecord?repo={repo}&collection={collection}&rkey={rkey}"
        async with httpx.AsyncClient() as client:
            r = await client.get(url)
            return r.json()["cid"]
    except Exception:
        return "bafyreihjdbd4zq4f4a5v6w5z5g5q5j5j5j5j5j5j5j5j5j5j5j5j5j5j5j5j5j"

async def get_post_text(uri: str) -> str:
    try:
        parts = uri.split("/")
        repo, rkey = parts[2], parts[4]
        url = f"https://bsky.social/xrpc/com.atproto.repo.getRecord?repo={repo}&collection=app.bsky.feed.post&rkey={rkey}"
        async with httpx.AsyncClient() as client:
            r = await client.get(url)
            r.raise_for_status()
            return r.json()["value"]["text"]
    except Exception:
        return ""

async def bluesky_stream():
    print("📡 Connecting to Bluesky event stream...")
    url = "https://bsky.social/xrpc/com.atproto.sync.subscribeRepos"
    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream("GET", url, headers={"Authorization": f"Bearer {BLUESKY_TOKEN}"}) as resp:
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
                    if not txt.lower().strip().startswith("check"): continue

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

async def post_reply(text: str, reply_to_uri: str):
    cid = await get_record_cid(reply_to_uri)
    url = "https://bsky.social/xrpc/com.atproto.repo.createRecord"
    payload = {
        "$type": "app.bsky.feed.post",
        "text": text,
        "reply": {"root": {"uri": reply_to_uri, "cid": cid}, "parent": {"uri": reply_to_uri, "cid": cid}},
        "createdAt": datetime.datetime.utcnow().isoformat() + "Z"
    }
    async with httpx.AsyncClient() as client:
        await client.post(
            url,
            headers={
                "Authorization": f"Bearer {BLUESKY_TOKEN}",
                "Content-Type": "application/json"
            },
            json=payload,
        )

async def main():
    print("✅ Bot started. Posting startup message...")
    try:
        await post_to_bluesky("✅ Bot started")
    except Exception as e:
        print(f"[ERROR] Failed to post startup message: {e}")

    print("👂 Listening for 'check' mentions or commands from owner...")
    async for txt, uri, author_did, reply_to_uri in bluesky_stream():
        print(f"📬 Received request: {txt[:50]}...")
        try:
            if reply_to_uri:
                parent_text = await get_post_text(reply_to_uri)
                prompt = f"Parent post: {parent_text}\n\nUser comment: {txt}"
            else:
                content = txt[len("check"):].strip()
                prompt = f"User request: {content}"

            reply = ask_local(prompt)
            await post_reply(reply, uri)
            print(f"[{datetime.datetime.utcnow()}] Replied to {uri}")

            # Post confirmation
            await post_to_bluesky("📨 Processed a 'check' request")
        except Exception as e:
            print(f"[ERROR] Failed to process {uri}: {e}")

if __name__ == "__main__":
    asyncio.run(main())
