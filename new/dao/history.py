from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from model.history import History

async def create_history(db: AsyncSession, session_id: str, role: str, content: str):
    stmt = insert(History).values(session_id=session_id, role=role, content=content)
    await db.execute(stmt)
    await db.commit()


async def get_last_10_history(db: AsyncSession, session_id: str):
    stmt = (
        select(History)
        .where(History.session_id == session_id)
        .order_by(desc(History.created_at))  # newest first
        .limit(10)
    )
    result = await db.execute(stmt)
    return result.scalars().all()