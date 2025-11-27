from sqlalchemy import insert
from app.db.database import async_session_maker
from app.db.models import Channels


class ImportChannelsService:

    @staticmethod
    async def import_usernames(usernames: list[str]):
        async with async_session_maker() as session:
            for u in usernames:
                stmt = insert(Channels).values(
                    username=u,
                    title=None,
                    description=None,
                    subscribers=0
                ).on_conflict_do_nothing(index_elements=["username"])
                await session.execute(stmt)

            await session.commit()
