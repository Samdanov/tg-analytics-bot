import asyncio
from typing import Optional

from openai import OpenAI

from app.core.config import config
from app.core.logging import get_logger

logger = get_logger(__name__)

client = OpenAI(api_key=config.openai_api_key)


async def ask_llm(prompt: str, max_tokens: int = 512, timeout: float = 30.0, retries: int = 2) -> str:
    """
    Отправляет запрос в LLM с таймаутом и небольшим числом ретраев.
    """
    last_exc: Optional[Exception] = None

    for attempt in range(retries + 1):
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    client.chat.completions.create,
                    model="gpt-5.1-mini",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                    temperature=0.2,
                ),
                timeout=timeout,
            )
            return response.choices[0].message.content
        except Exception as exc:
            last_exc = exc
            if attempt >= retries:
                break
            delay = 2 ** attempt
            logger.warning("LLM retry %s/%s after error: %s", attempt + 1, retries, exc)
            await asyncio.sleep(delay)

    raise last_exc if last_exc else RuntimeError("LLM request failed without exception")
