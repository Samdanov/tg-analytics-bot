from openai import OpenAI
from core.config import config

client = OpenAI(api_key=config.openai_api_key)


async def ask_llm(prompt: str, max_tokens: int = 512) -> str:
    """
    Безопасный вызов OpenAI.
    Модель — 5.1-mini (дёшево и достаточно умно).
    Лимитируем расход токенов.
    """

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=0.2
    )

    return response.choices[0].message["content"]
