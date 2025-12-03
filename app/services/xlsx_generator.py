# app/services/xlsx_generator.py

import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from sqlalchemy import select

# ⚠️ Если у тебя импорты без префикса app., поменяй на:
# from db.database import async_session_maker
# from db.models import Channel, AnalyticsResults
from app.db.database import async_session_maker
from app.db.models import Channel, AnalyticsResults


def _auto_width(ws):
    """Автоматически подгоняем ширину колонок под содержимое."""
    for column in ws.columns:
        max_length = 0
        column_letter = get_column_letter(column[0].column)

        for cell in column:
            try:
                value = str(cell.value) if cell.value is not None else ""
            except Exception:
                value = ""
            max_length = max(max_length, len(value))

        ws.column_dimensions[column_letter].width = min(max_length + 2, 80)


async def _load_source_channel(channel_username: str) -> Optional[Channel]:
    """Находим канал по username."""
    async with async_session_maker() as session:
        q = select(Channel).where(Channel.username == channel_username)
        res = await session.execute(q)
        return res.scalar_one_or_none()


async def _load_similar_results(source_channel_id: int) -> tuple[Optional[AnalyticsResults], List[int]]:
    """
    Берём последний AnalyticsResults для канала
    и список id похожих каналов в нужном порядке.
    """
    async with async_session_maker() as session:
        q = (
            select(AnalyticsResults)
            .where(AnalyticsResults.channel_id == source_channel_id)
            .order_by(AnalyticsResults.created_at.desc())
            .limit(1)
        )
        res = await session.execute(q)
        row: Optional[AnalyticsResults] = res.scalar_one_or_none()

    if not row or not row.similar_channels_json:
        return None, []

    try:
        raw = json.loads(row.similar_channels_json)
        if not isinstance(raw, list):
            return row, []

        # предполагаем структуру [{'channel_id': int, 'score': float}, ...]
        ids = [int(item["channel_id"]) for item in raw if "channel_id" in item]
        return row, ids
    except Exception:
        return row, []


async def _load_channels_by_ids(ids: List[int]) -> Dict[int, Channel]:
    """Берём из БД все каналы с нужными id."""
    if not ids:
        return {}

    async with async_session_maker() as session:
        q = select(Channel).where(Channel.id.in_(ids))
        res = await session.execute(q)
        rows: List[Channel] = res.scalars().all()

    return {c.id: c for c in rows}


async def generate_similar_channels_xlsx(
    source_username: str,
    base_dir: Optional[Path] = None,
) -> Path:
    """
    Генерирует XLSX-файл в формате skladtech_expo_*:
    одна таблица:
    - Релевантность, %
    - Имя канала (ссылка)
    - Подписчики
    - Название канала
    - Описание канала
    """

    # 1) Находим исходный канал
    if source_username.startswith("@"):
        source_username = source_username[1:]

    source_channel = await _load_source_channel(source_username)
    if not source_channel:
        raise ValueError(f"Канал @{source_username} не найден в БД")

    # 2) Берём последний результат similarity
    last_result, similar_ids = await _load_similar_results(source_channel.id)
    if not last_result or not similar_ids:
        raise ValueError("Для этого канала ещё нет рассчитанных похожих каналов.")

    # 3) Подгружаем каналы по id
    channels_map = await _load_channels_by_ids(similar_ids)

    # 4) Разбираем JSON с похожими каналами
    similar_list: List[Dict[str, Any]] = []
    try:
        raw = json.loads(last_result.similar_channels_json)
        if isinstance(raw, list):
            similar_list = raw
    except Exception:
        similar_list = []

    # 5) Готовим Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Каналы"

    # Заголовки как в skladtech_expo
    ws.append([
        "Дата создания",
        "Релевантность, %",
        "Имя канала",
        "Подписчики",
        "Название канала",
        "Описание канала",
    ])

    created_at = last_result.created_at or datetime.utcnow()
    created_str = created_at.strftime("%d.%m.%Y")

    # 6) Заполняем строки
    for item in similar_list:
        ch_id = item.get("channel_id")
        score = float(item.get("score", 0.0))
        ch = channels_map.get(ch_id)

        if not ch:
            continue

        relevance_percent = round(score * 100, 1)
        link = f"https://t.me/{ch.username}" if ch.username else ""

        ws.append([
            created_str,
            relevance_percent,
            link,
            getattr(ch, "subscribers", None),
            getattr(ch, "title", None),
            getattr(ch, "description", None),
        ])

    _auto_width(ws)

    # 7) Путь и сохранение
    if base_dir is None:
        # два уровня вверх от текущего файла → корень проекта
        base_dir = Path(__file__).resolve().parents[2]

    reports_dir = base_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_username = (source_channel.username or f"id_{source_channel.id}").replace("@", "")
    filename = reports_dir / f"similar_channels_{safe_username}_{ts}.xlsx"

    wb.save(filename)
    return filename
