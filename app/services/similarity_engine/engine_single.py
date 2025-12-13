import json
from typing import List, Dict, Set
from math import log, sqrt

from sqlalchemy import delete

from app.db.database import async_session_maker
from app.db.models import AnalyticsResults
from app.core.logging import get_logger
from app.services.similarity_engine.shared import (
    is_noise_channel,
    load_keywords_corpus,
)

logger = get_logger(__name__)


async def calculate_similarity_for_channel(
    target_channel_id: int,
    top_n: int = 10,
    max_df_ratio: float = 0.3,
    min_keywords_per_channel: int = 4,
    min_similarity_threshold: float = 0.0,  # Убран порог - возвращаем топ-N
) -> bool:
    """
    Лёгкий по памяти расчёт похожих каналов для одного channel_id.
    Использует полноценный TF-IDF + Cosine Similarity для точного расчёта схожести.
    
    Args:
        target_channel_id: ID целевого канала
        top_n: Количество похожих каналов для возврата (возвращает TOP-N по score)
        max_df_ratio: Фильтр частых слов (default 0.3 = слова встречающиеся в >30% каналов)
        min_keywords_per_channel: Минимум ключевых слов на канал
        min_similarity_threshold: Минимальный порог схожести (default 0.0 = без фильтра)
    
    Returns:
        True если расчёт успешен, False если нет данных
    
    Note:
        Порог по умолчанию = 0 (отключён). Возвращается TOP-N каналов по score,
        независимо от абсолютного значения схожести. Пользователь запрашивает
        N каналов - он получает N лучших.
    """
    logger.info("ENGINE_SINGLE v2.2 run target=%s", target_channel_id)

    raw_tokens_by_channel, meta_by_channel = await load_keywords_corpus()

    if target_channel_id not in raw_tokens_by_channel:
        async with async_session_maker() as session:
            await session.execute(
                delete(AnalyticsResults).where(AnalyticsResults.channel_id == target_channel_id)
            )
            session.add(
                AnalyticsResults(
                    channel_id=target_channel_id,
                    similar_channels_json=json.dumps([]),
                )
            )
            await session.commit()
        return False

    filtered_tokens_by_channel: Dict[int, List[str]] = {}
    for cid, tokens in raw_tokens_by_channel.items():
        meta = meta_by_channel.get(cid, {})
        if cid != target_channel_id and is_noise_channel(meta.get("username"), meta.get("title"), tokens):
            continue
        filtered_tokens_by_channel[cid] = tokens

    if target_channel_id not in filtered_tokens_by_channel:
        async with async_session_maker() as session:
            await session.execute(
                delete(AnalyticsResults).where(AnalyticsResults.channel_id == target_channel_id)
            )
            session.add(
                AnalyticsResults(
                    channel_id=target_channel_id,
                    similar_channels_json=json.dumps([]),
                )
            )
            await session.commit()
        return False

    df: Dict[str, int] = {}
    for tokens in filtered_tokens_by_channel.values():
        for t in set(tokens):
            df[t] = df.get(t, 0) + 1

    num_docs = len(filtered_tokens_by_channel)
    if num_docs < 2:
        async with async_session_maker() as session:
            await session.execute(
                delete(AnalyticsResults).where(AnalyticsResults.channel_id == target_channel_id)
            )
            session.add(
                AnalyticsResults(
                    channel_id=target_channel_id,
                    similar_channels_json=json.dumps([]),
                )
            )
            await session.commit()
        return False

    frequent_tokens: Set[str] = set()
    for t, count in df.items():
        if count / num_docs > max_df_ratio:
            frequent_tokens.add(t)

    cleaned_by_channel: Dict[int, List[str]] = {}
    for cid, tokens in filtered_tokens_by_channel.items():
        cleaned = [t for t in tokens if t not in frequent_tokens]
        if len(cleaned) < min_keywords_per_channel:
            continue
        cleaned_by_channel[cid] = cleaned

    if target_channel_id not in cleaned_by_channel or len(cleaned_by_channel) < 2:
        async with async_session_maker() as session:
            await session.execute(
                delete(AnalyticsResults).where(AnalyticsResults.channel_id == target_channel_id)
            )
            session.add(
                AnalyticsResults(
                    channel_id=target_channel_id,
                    similar_channels_json=json.dumps([]),
                )
            )
            await session.commit()
        return False

    # IDF weights
    idf = {t: log(num_docs / (1 + df_val)) for t, df_val in df.items() if t not in frequent_tokens}

    target_tokens = cleaned_by_channel[target_channel_id]
    target_set = set(target_tokens)
    
    # TF-IDF vector для целевого канала (только для токенов с IDF)
    target_tf = {}
    for t in target_tokens:
        if t in idf:  # Учитываем только токены с IDF
            target_tf[t] = target_tf.get(t, 0) + 1
    
    target_tfidf = {t: tf * idf[t] for t, tf in target_tf.items()}
    target_norm = sqrt(sum(v**2 for v in target_tfidf.values())) or 1.0

    pairs = []
    all_scores = []  # Для логирования
    filtered_by_threshold = 0
    
    for cid, tokens in cleaned_by_channel.items():
        if cid == target_channel_id:
            continue
        
        common = target_set.intersection(tokens)
        if not common:
            continue
        
        # TF-IDF vector для кандидата (только для токенов с IDF)
        candidate_tf = {}
        for t in tokens:
            if t in idf:  # Учитываем только токены с IDF
                candidate_tf[t] = candidate_tf.get(t, 0) + 1
        
        candidate_tfidf = {t: tf * idf[t] for t, tf in candidate_tf.items()}
        candidate_norm = sqrt(sum(v**2 for v in candidate_tfidf.values())) or 1.0
        
        # Косинусное сходство (dot product / (norm_a * norm_b))
        dot_product = sum(
            target_tfidf.get(t, 0.0) * candidate_tfidf.get(t, 0.0) 
            for t in common if t in idf
        )
        
        score = dot_product / (target_norm * candidate_norm) if (target_norm * candidate_norm) > 0 else 0.0
        all_scores.append(score)
        
        # Фильтруем по минимальному порогу схожести (по умолчанию 0 = без фильтра)
        # Возвращаем TOP-N по score независимо от абсолютного значения
        if min_similarity_threshold > 0 and score < min_similarity_threshold:
            filtered_by_threshold += 1
            continue
            
        pairs.append((cid, float(score)))

    pairs.sort(key=lambda x: x[1], reverse=True)
    
    # Детальное логирование
    if all_scores:
        all_scores_sorted = sorted(all_scores, reverse=True)
        max_score_all = all_scores_sorted[0] if all_scores_sorted else 0.0
        avg_score_all = sum(all_scores) / len(all_scores) if all_scores else 0.0
        
        logger.info(
            f"ENGINE_SINGLE stats: "
            f"candidates={len(all_scores)}, "
            f"passed_threshold={len(pairs)}, "
            f"filtered={filtered_by_threshold}, "
            f"max_score={max_score_all:.3f} ({max_score_all*100:.1f}%), "
            f"avg_score={avg_score_all:.3f} ({avg_score_all*100:.1f}%), "
            f"threshold={min_similarity_threshold:.2f} ({min_similarity_threshold*100:.0f}%)"
        )
        
        # Если ничего не прошло порог, показываем топ-5 scores для отладки
        if not pairs and all_scores_sorted:
            top5 = all_scores_sorted[:5]
            logger.warning(
                f"ENGINE_SINGLE: NO results passed threshold! Top 5 scores: "
                f"{', '.join(f'{s:.3f} ({s*100:.1f}%)' for s in top5)}"
            )
    else:
        logger.warning(f"ENGINE_SINGLE: No candidates with common keywords found!")
    
    # Логируем статистику схожести прошедших каналов
    if pairs:
        min_score = pairs[-1][1] if pairs else 0.0
        max_score_actual = pairs[0][1] if pairs else 0.0
        avg_score = sum(s for _, s in pairs) / len(pairs) if pairs else 0.0
        logger.info(
            f"ENGINE_SINGLE results: found={len(pairs)}, "
            f"min={min_score:.3f} ({min_score*100:.1f}%), "
            f"max={max_score_actual:.3f} ({max_score_actual*100:.1f}%), "
            f"avg={avg_score:.3f} ({avg_score*100:.1f}%)"
        )
    
    if top_n is not None and top_n > 0:
        pairs = pairs[:top_n]

    async with async_session_maker() as session:
        await session.execute(
            delete(AnalyticsResults).where(AnalyticsResults.channel_id == target_channel_id)
        )
        payload = json.dumps(
            [{"channel_id": cid, "score": score} for cid, score in pairs]
        )
        session.add(
            AnalyticsResults(
                channel_id=target_channel_id,
                similar_channels_json=payload,
            )
        )
        await session.commit()

    logger.info("ENGINE_SINGLE finished target=%s results=%s", target_channel_id, len(pairs))
    return True
