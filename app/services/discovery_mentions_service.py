import re
from typing import List, Set

from app.db.repo import get_pool

# Регекс для поиска username в тексте
USERNAME_RE = re.compile(
    r"(?:@|https?://t\.me/)([a-zA-Z0-9_]{4,64})",
    re.IGNORECASE
)

class DiscoveryMentionsService:
    """
    Ищет новые каналы через упоминания @username
    в текстах постов.
    """

    async def extract_usernames_from_posts(self) -> Set[str]:
        """
        Достаёт все username из posts.text
        """
        pool = await get_pool()

        query = """
            SELECT text FROM posts
            WHERE text IS NOT NULL
        """

        result_usernames: Set[str] = set()

        async with pool.acquire() as conn:
            rows = await conn.fetch(query)

            for r in rows:
                text = r["text"]
                found = USERNAME_RE.findall(text)

                for u in found:
                    u = u.lower()

                    # Фильтрация ботов и мусора
                    if u.endswith("bot"):
                        continue
                    if len(u) < 4:
                        continue

                    result_usernames.add(u)

        return result_usernames

    async def save_new_usernames(self, usernames: List[str]) -> int:
        """
        Записывает username в таблицу channels,
        если их там ещё нет.
        """
        pool = await get_pool()
        added = 0

        insert_q = """
            INSERT INTO channels (username)
            VALUES ($1)
            ON CONFLICT (username) DO NOTHING
        """

        async with pool.acquire() as conn:
            async with conn.transaction():
                for u in usernames:
                    res = await conn.execute(insert_q, u)
                    if res == "INSERT 0 1":
                        added += 1

        return added
