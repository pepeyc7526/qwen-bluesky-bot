#!/usr/bin/env python3
import os, json, datetime, asyncio, httpx

# ---------- CONFIGURATION ----------
BLUESKY_TOKEN = os.getenv("BLUESKY_TOKEN")          # token of the BOT account
HF_TOKEN      = os.getenv("HF_TOKEN")               # free Hugging Face Read token
BOT_HANDLE    = "lumobot-pepeyc7526.bsky.social"    # handle of the BOT account
BOT_DID       = "did:plc:er457dupy7iytuzdgfmfsuv7"  # DID of the BOT account
OWNER_DID     = "did:plc:topho472iindqxv5hm7nzww2" # your DID (to allow direct commands)
MAX_LEN       = 300
ELLIPSIS      = "…"

HF_MODEL      = "microsoft/Phi-3-mini-4k-instruct"
HF_API_URL    = f"https://api-inference.huggingface.co/models/{HF_MODEL}"
# ------------------------------------

if not BLUESKY_TOKEN:
    raise RuntimeError("BLUESKY_TOKEN missing – add it as a secret")
if not HF_TOKEN:
    raise RuntimeError("HF_TOKEN missing – get free token at huggingface.co")

async def get_record_cid(uri: str):
    """Fetch the CID for a given URI."""
    try:
        parts = uri.split("/")
        if len(parts) < 5:
            return None
        repo, collection, rkey = parts[2], parts[3], parts[4]
        url = f"https://bsky.social/xrpc/com.atproto.repo.getRecord?repo={repo}&collection={collection}&rkey={rkey}"
        async with httpx.AsyncClient() as client:
            r = await client.get(url)
            r.raise_for_status()
            return r.json()["cid"]
    except Exception:
        return None

async def bluesky_stream():
    url = "https://bsky.social/xrpc/com.atproto.sync.subscribeRepos"
    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream(
            "GET", url,
            headers={"Authorization": f"Bearer {BLUESKY_TOKEN}"}
        ) as resp:
            async for line in resp.aiter_lines():
                if not line.strip():
                    continue
                try:
                    ev = json.loads(line)
                except Exception:
                    continue
                if ev.get("$type") != "com.atproto.sync.subscribeRepos#commit":
                    continue
                for op in ev.get("ops", []):
                    if op.get("action") != "create" or "post" not in op.get("path", ""):
                        continue
                    rec = op.get("payload", {})
                    if rec.get("$type") != "app.bsky.feed.post":
                        continue
                    txt = rec.get("text", "")
                    uri = rec.get("uri", "")
                    author_did = ev.get("repo", "")  # repo field is the author's DID

                    # Allow if mentions bot OR from owner
                    mentioned = f"@{BOT_HANDLE}" in txt.lower()
                    from_owner = (author_did == OWNER_DID)

                    if not (mentioned or from_owner):
                        continue

                    if not txt.lower().strip().startswith("check"):
                        continue

                    yield txt, uri, author_did

async def ask_hf(prompt: str) -> str:
    full_prompt = (
        "You are a helpful assistant that provides concise fact-checks. "
        "Respond in under 300 characters, without links or emojis.\n\n"
        f"User: {prompt}\nAssistant:"
    )
    payload = {
        "inputs": full_prompt,
        "parameters": {
            "max_new_tokens": 100,
            "return_full_text": False,
            "temperature": 0.3
        }
    }
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(HF_API_URL, headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()

    if isinstance(data, list) and len(data) > 0:
        answer = data[0].get("generated_text", "").strip()
    else:
        answer = str(data.get("error", "Unknown error"))

    answer = " ".join(answer.split())
    if len(answer) > MAX_LEN:
        answer = answer[:MAX_LEN - len(ELLIPSIS)] + ELLIPSIS
    return answer

async def post_reply(text: str, reply_to_uri: str):
    cid = await get_record_cid(reply_to_uri)
    if not cid:
        print(f"Warning: Could not fetch CID for {reply_to_uri}. Using placeholder.")
        cid = "bafyreihjdbd4zq4f4a5v6w5z5g5q5j5j5j5j5j5j5j5j5j5j5j5j5j5j5j5j5j"  # dummy CID

    url = "https://bsky.social/xrpc/com.atproto.repo.createRecord"
    payload = {
        "$type": "app.bsky.feed.post",
        "text": text,
        "reply": {
            "root": {"uri": reply_to_uri, "cid": cid},
            "parent": {"uri": reply_to_uri, "cid": cid}
        },
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
    async for txt, uri, author_did in bluesky_stream():
        content = txt[len("check"):].strip()
        if not content:
            continue

        prompt = f"Provide a concise fact-check of the following claim:\n\n{content}"
        try:
            reply = await ask_hf(prompt)
            await post_reply(reply, uri)
            print(f"[{datetime.datetime.utcnow()}] Replied to {uri} by {author_did}")
        except Exception as e:
            print(f"[ERROR] Failed to process {uri}: {e}")

if __name__ == "__main__":
    asyncio.run(main())
