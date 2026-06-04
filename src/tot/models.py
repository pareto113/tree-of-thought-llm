import os
import requests
import backoff

completion_tokens = prompt_tokens = 0

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Injected into every call to enforce strict output format.
# qwen2.5:14b-instruct tends to add markdown/bullets without this.
_SYSTEM_PROMPT = (
    "You are a precise assistant. Follow the output format shown in the examples exactly. "
    "Output only what is asked. Do not add markdown formatting, bullet points, bold text, "
    "or explanations beyond the format shown."
)


@backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=5)
def _chat(payload: dict) -> dict:
    resp = requests.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload, timeout=300)
    resp.raise_for_status()
    return resp.json()


def gpt(prompt, model="qwen2.5:14b-instruct", temperature=0.7, max_tokens=1000, n=1, stop=None) -> list:
    messages = [{"role": "user", "content": prompt}]
    return chatgpt(messages, model=model, temperature=temperature, max_tokens=max_tokens, n=n, stop=stop)


def chatgpt(messages, model="qwen2.5:14b-instruct", temperature=0.7, max_tokens=1000, n=1, stop=None) -> list:
    global completion_tokens, prompt_tokens

    full_messages = [{"role": "system", "content": _SYSTEM_PROMPT}] + messages

    options = {"temperature": temperature, "num_predict": max_tokens}
    if stop:
        options["stop"] = stop if isinstance(stop, list) else [stop]

    payload = {
        "model": model,
        "messages": full_messages,
        "stream": False,
        "options": options,
    }

    outputs = []
    for _ in range(n):
        data = _chat(payload)
        outputs.append(data["message"]["content"])
        completion_tokens += data.get("eval_count", 0)
        prompt_tokens += data.get("prompt_eval_count", 0)

    return outputs


def gpt_usage(backend="qwen2.5:14b-instruct"):
    global completion_tokens, prompt_tokens
    # Local model — no API cost
    return {"completion_tokens": completion_tokens, "prompt_tokens": prompt_tokens, "cost": 0.0}
