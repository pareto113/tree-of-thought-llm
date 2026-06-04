import os
import backoff
from openai import OpenAI

completion_tokens = prompt_tokens = 0

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))


@backoff.on_exception(backoff.expo, Exception, max_tries=5)
def completions_with_backoff(**kwargs):
    return client.chat.completions.create(**kwargs)


def gpt(prompt, model="gpt-4o-mini", temperature=0.7, max_tokens=1000, n=1, stop=None) -> list:
    messages = [{"role": "user", "content": prompt}]
    return chatgpt(messages, model=model, temperature=temperature, max_tokens=max_tokens, n=n, stop=stop)


def chatgpt(messages, model="gpt-4o-mini", temperature=0.7, max_tokens=1000, n=1, stop=None) -> list:
    global completion_tokens, prompt_tokens
    outputs = []
    while n > 0:
        cnt = min(n, 20)
        n -= cnt
        res = completions_with_backoff(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            n=cnt,
            stop=stop,
        )
        outputs.extend([choice.message.content for choice in res.choices])
        completion_tokens += res.usage.completion_tokens
        prompt_tokens += res.usage.prompt_tokens
    return outputs


def gpt_usage(backend="gpt-4o-mini"):
    global completion_tokens, prompt_tokens
    # (input $/1K, output $/1K)
    pricing = {
        "gpt-4":         (0.03,     0.06),
        "gpt-3.5-turbo": (0.0015,   0.002),
        "gpt-4o":        (0.0025,   0.01),
        "gpt-4o-mini":   (0.00015,  0.0006),
    }
    in_per_k, out_per_k = pricing.get(backend, (0.03, 0.06))
    cost = prompt_tokens / 1000 * in_per_k + completion_tokens / 1000 * out_per_k
    return {"completion_tokens": completion_tokens, "prompt_tokens": prompt_tokens, "cost": cost}
