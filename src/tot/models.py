import os
import backoff
import openai

_client = openai.OpenAI()  # reads OPENAI_API_KEY from env

# 형식 강제용 시스템 프롬프트 — GPT-4o mini가 few-shot 형식을 이탈해 번호 목록·마크다운을
# 추가하는 현상을 막는다. Qwen용 언어 지시와 달리 형식 준수만을 목적으로 한다.
_SYSTEM_PROMPT = (
    "You are a concise assistant. "
    "Follow the output format shown in the examples exactly. "
    "Do not add explanations, numbered lists, markdown, or any text beyond what the format requires."
)

completion_tokens = prompt_tokens = 0

# gpt-4o-mini pricing (per 1M tokens)
_PRICING = {
    "gpt-4o-mini":         {"input": 0.15,  "output": 0.60},
    "gpt-4o":              {"input": 2.50,  "output": 10.00},
    "gpt-4":               {"input": 30.00, "output": 60.00},
    "gpt-3.5-turbo":       {"input": 0.50,  "output": 1.50},
}


@backoff.on_exception(
    backoff.expo,
    (openai.RateLimitError, openai.APIConnectionError, openai.InternalServerError),
    max_tries=8,
)
def _create(**kwargs) -> openai.types.chat.ChatCompletion:
    return _client.chat.completions.create(**kwargs)


def gpt(prompt, model="gpt-4o-mini", temperature=0.7, max_tokens=1000, n=1, stop=None) -> list:
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    return chatgpt(messages, model=model, temperature=temperature, max_tokens=max_tokens, n=n, stop=stop)


def chatgpt(messages, model="gpt-4o-mini", temperature=0.7, max_tokens=1000, n=1, stop=None) -> list:
    global completion_tokens, prompt_tokens

    response = _create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        n=n,
        stop=stop,
    )

    completion_tokens += response.usage.completion_tokens
    prompt_tokens += response.usage.prompt_tokens

    return [choice.message.content for choice in response.choices]


def gpt_usage(backend="gpt-4o-mini") -> dict:
    global completion_tokens, prompt_tokens
    pricing = _PRICING.get(backend, {"input": 0.0, "output": 0.0})
    cost = (prompt_tokens * pricing["input"] + completion_tokens * pricing["output"]) / 1_000_000
    return {"completion_tokens": completion_tokens, "prompt_tokens": prompt_tokens, "cost": cost}
