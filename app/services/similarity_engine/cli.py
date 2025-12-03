import asyncio
from .engine import SimilarityEngine

async def main():
    engine = SimilarityEngine(top_n=10)
    await engine.calculate_similarity()

if __name__ == "__main__":
    asyncio.run(main())
