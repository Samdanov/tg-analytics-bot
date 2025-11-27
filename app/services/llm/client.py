from openai import OpenAI
from app.core.config import config

client = OpenAI(api_key=config.openai_api_key)


async def ask_llm(prompt: str, max_tokens: int = 512) -> str:
    print("DEBUG OPENAI KEY:", config.openai_api_key[:8])  # временный вывод

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "user", "content": prompt}
        ],
        max_tokens=max_tokens,
        temperature=0.2
    )

    # ВАЖНО: новая структура ответа в openai 2.x
    return response.choices[0].message.content
