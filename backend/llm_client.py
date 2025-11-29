# llm_client.py
import os
import httpx
from typing import List, Dict

LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "openai")  # "openai" or "hf"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")  # change as needed

async def call_openai(messages: List[Dict[str,str]]):
    # using OpenAI chat completions v1 (httpx)
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": OPENAI_MODEL,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 800
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(url, json=payload, headers=headers)
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"]

async def generate_reply(history_msgs):
    # history_msgs: list of {"role":"user"/"assistant", "content": "..."}
    if LLM_PROVIDER == "openai":
        return await call_openai(history_msgs)
    else:
        raise RuntimeError("Unsupported LLM provider in demo")
