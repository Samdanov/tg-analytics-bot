from app.services.similarity_engine.engine_single import calculate_similarity_for_channel
from app.services.similarity_engine.engine import SimilarityEngine


async def recalc_for_channel(channel_id: int, top_n: int = 10) -> bool:
    return await calculate_similarity_for_channel(channel_id, top_n=top_n)


async def recalc_all(top_n: int = 10) -> None:
    engine = SimilarityEngine(top_n=top_n)
    await engine.calculate_similarity()
