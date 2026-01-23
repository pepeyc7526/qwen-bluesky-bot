#!/usr/bin/env python3
import os, json, datetime, asyncio, httpx
from llama_cpp import Llama

BOT_HANDLE    = os.getenv("BOT_HANDLE", "bot-pepeyc7526.bsky.social")
BOT_PASSWORD  = os.getenv("BOT_PASSWORD")
BOT_DID       = "did:plc:er457dupy7iytuzdgfmfsuv7"
OWNER_DID     = "did:plc:topho472iindqxv5hm7nzww2"
MAX_LEN       = 300
LAST_POST_FILE = "last_processed_post.txt"
SEARCH_USAGE_FILE = "search_usage.json"

MODEL_PATH = "models/qwen2-7b-instruct-q4_k_m.gguf"
llm = Llama(model_path=MODEL_PATH, n_ctx=2048, n_threads=2, verbose=False)

if not BOT_PASSWORD:
    raise RuntimeError("BOT_PASSWORD missing")

# === ВЕБ-ПОИСК ===
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

# === ОСТАЛЬНЫЕ ФУНКЦИИ БЕЗ ИЗМЕНЕНИЙ ===
# (get_fresh_token, post_to_bluesky, get_record_cid, get_post_text, get_author_feed, mark_as_read, post_reply)

def ask_local(prompt: str, use_web_context=False) -> str:
    system_msg = (
        "You are a helpful AI assistant. "
        "Use the provided context to answer accurately. "
        "If no context, give a general answer. "
        "Keep under 300 characters. Never use links or emojis."
    )
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": prompt}
    ]
    
    full_prompt = ""
    for msg in messages:
        if msg["role"] == "user":
            full_prompt += f"<|im_start|>user\n{msg['content']}<|im_end|>\n"
        elif msg["role"] == "assistant":
            full_prompt += f"<|im_start|>assistant\n{msg['content']}<|im_end|>\n"
        else:
            full_prompt += f"<|im_start|>system\n{msg['content']}<|im_end|>\n"
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

# === MAIN ===
async def main():
    token = await get_fresh_token()
    print("✅ Checking only YOUR requests...")

    # Сброс счётчика, если новый месяц
    if should_reset_counter():
        save_search_usage(0)
        print("📅 Search counter reset for new month")

    last_uri = get_last_processed_uri()
    print(f"⏭️ Skipping posts before: {last_uri}")

    feed = await get_author_feed(OWNER_DID, token)
    replied_uri = None

    for item in feed[:10]:
        post = item.get("post", {})
        record = post.get("record", {})
        if record.get("$type") != "app.bsky.feed.post":
            continue

        uri = post.get("uri", "")
        if not uri:
            continue

        if last_uri and uri == last_uri:
            break

        txt = record.get("text", "")
        clean_txt = txt.strip()

        replied = False

        # === ОБРАБОТКА ЗАПРОСОВ ===
        if clean_txt.lower().startswith("ai web "):
            # Веб-поиск
            content = clean_txt[5:].strip()
            if content:
                usage = load_search_usage()
                if usage["count"] >= 100:
                    reply = "🔍 Web search limit reached (100/month). Try again next month!"
                else:
                    print(f"🌐 Web search ({usage['count']+1}/100): {content}")
                    context = await web_search(content)
                    if context:
                        prompt = f"Context: {context}\nQuestion: {content}"
                    else:
                        prompt = f"Question: {content}"
                    reply = ask_local(prompt)
                    # Сохраняем счётчик
                    save_search_usage(usage["count"] + 1)
                await post_reply(reply, uri, token)
                print(f"✅ Replied (web) to {uri}")
                replied_uri = uri
                replied = True

        elif clean_txt.lower().startswith("ai "):
            # Локальная модель
            content = clean_txt[3:].strip()
            if content:
                reply = ask_local(f"Question: {content}")
                await post_reply(reply, uri, token)
                print(f"✅ Replied (local) to {uri}")
                replied_uri = uri
                replied = True

        elif clean_txt.startswith("@bot-pepeyc7526.bsky.social"):
            content = clean_txt[len("@bot-pepeyc7526.bsky.social"):].strip()
            if content:
                reply = ask_local(f"Question: {content}")
                await post_reply(reply, uri, token)
                print(f"✅ Replied (mention) to {uri}")
                replied_uri = uri
                replied = True

        if replied:
            break

    if replied_uri:
        save_last_processed_uri(replied_uri)

    seen_at = datetime.datetime.utcnow().isoformat() + "Z"
    await mark_as_read(token, seen_at)
    print("✅ Done")

# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===
def get_last_processed_uri():
    if os.path.exists(LAST_POST_FILE):
        with open(LAST_POST_FILE, "r") as f:
            return f.read().strip()
    return None

def save_last_processed_uri(uri):
    with open(LAST_POST_FILE, "w") as f:
        f.write(uri)

# ... остальные функции (get_fresh_token, post_to_bluesky и т.д.) — как в предыдущей версии
