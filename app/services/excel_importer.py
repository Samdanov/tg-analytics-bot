# app/services/excel_importer.py

import re
import pandas as pd
from typing import List, Optional

from app.db.repo import get_pool, save_channel
from app.services.llm.analyzer import save_analysis


STOPWORDS = {
    "и","в","на","к","для","о","от","по","с","за","у",
    "это","тот","эта","эти","как","но","или","да","не",
    "мы","вы","они","он","она","так","же","из","про",
    "над","под","что","то","бы","а","ну",
    "the","and","for","with","you","your","from","this","that"
}


def extract_keywords(text: str, limit: int = 20) -> List[str]:
    if not text:
        return []
    text = text.lower()
    tokens = re.findall(r"[a-zа-яё0-9]{3,}", text)

    freq = {}
    for t in tokens:
        if t in STOPWORDS:
            continue
        freq[t] = freq.get(t, 0) + 1

    return [w for w, _ in sorted(freq.items(), key=lambda x: -x[1])[:limit]]


async def import_channels_from_excel(path: str, max_rows: Optional[int] = None):
    print(f"[IMPORT] Читаю Excel: {path}")

    # ВАЖНО: header=1 → берем вторую строку как названия колонок
    df = pd.read_excel(path, header=1)

    if max_rows:
        df = df.iloc[:max_rows]

    print("[IMPORT] Строк к обработке:", len(df))

    pool = await get_pool()
    imported = 0

    for _, row in df.iterrows():

        # username
        username = str(row.get("username") or "").strip()
        username = username.replace("@", "").replace("https://t.me/", "").replace("http://t.me/", "")

        if not username:
            continue

        # title / description
        title = str(row.get("title") or "").strip()
        description = str(row.get("description") or "").strip()

        if not title:
            title = username
        if not description:
            description = title

        # subscribers
        try:
            subscribers = int(row.get("subscribers") or 0)
        except:
            subscribers = 0

        # category
        category = str(row.get("category") or "").strip()

        # build keywords
        full_text = f"{title} {description} {category} {username}"
        keywords = extract_keywords(full_text, limit=20)

        if not keywords:
            keywords = [username]

        # save channel
        try:
            channel_id = await save_channel(pool, {
                "username": username,
                "title": title,
                "description": description,
                "subscribers": subscribers
            })
        except Exception as e:
            print(f"[IMPORT] Ошибка сохранения @{username}: {e}")
            continue

        # save keywords_cache
        try:
            await save_analysis(channel_id, {
                "audience": "",
                "keywords": keywords
            })
        except Exception as e:
            print(f"[IMPORT] Ошибка keywords_cache @{username}: {e}")

        imported += 1
        if imported % 1000 == 0:
            print(f"[IMPORT] Импортировано каналов: {imported}")

    print(f"[IMPORT] Готово. Импортировано: {imported}")
    return imported
