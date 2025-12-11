# app/services/excel_importer.py

import re
import pandas as pd
from typing import List, Optional

from app.db.repo import save_channel
from app.services.llm.analyzer import save_analysis
from app.core.logging import get_logger

logger = get_logger(__name__)


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


async def import_channels_from_excel(path: str, max_rows: Optional[int] = None, min_subscribers: int = 0):
    logger.info("[IMPORT] читаю Excel: %s", path)

    df = pd.read_excel(path, header=1)

    if max_rows:
        df = df.iloc[:max_rows]

    logger.info("[IMPORT] строк к обработке: %s", len(df))

    imported = 0

    for _, row in df.iterrows():

        username = str(row.get("username") or "").strip()
        username = username.replace("@", "").replace("https://t.me/", "").replace("http://t.me/", "")

        if not username:
            continue

        title = str(row.get("title") or "").strip()
        description = str(row.get("description") or "").strip()

        if not title:
            title = username
        if not description:
            description = title

        try:
            subscribers = int(row.get("subscribers") or 0)
        except Exception:
            subscribers = 0

        if subscribers < min_subscribers:
            continue

        category = str(row.get("category") or "").strip()

        full_text = f"{title} {description} {category} {username}"
        keywords = extract_keywords(full_text, limit=20)

        if not keywords:
            keywords = [username]

        try:
            channel_id = await save_channel({
                "username": username,
                "title": title,
                "description": description,
                "subscribers": subscribers
            })
        except Exception as e:
            logger.error("[IMPORT] ошибка сохранения @%s: %s", username, e)
            continue

        try:
            await save_analysis(channel_id, {
                "audience": "",
                "keywords": keywords
            })
        except Exception as e:
            logger.error("[IMPORT] ошибка keywords_cache @%s: %s", username, e)

        imported += 1
        if imported % 1000 == 0:
            logger.info("[IMPORT] импортировано каналов: %s", imported)

    logger.info("[IMPORT] готово. Импортировано: %s", imported)
    return imported
