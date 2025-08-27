from datetime import datetime, timezone

from aiogram.types import User as AiogramUser
from sqlalchemy import select, delete, and_ , or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from database.models import Listing, User as DbUser

async def orm_get_listing(session: AsyncSession, message_id: int, chat_id: int) -> Listing | None:
    query = select(Listing).where(Listing.message_id == message_id,
                                  Listing.chat_id == chat_id)
    result = await session.execute(query)
    return result.scalar_one_or_none()

async def orm_get_active_listings(session: AsyncSession) -> list[Listing]:
    now = datetime.now(timezone.utc)

    query = (
        select(Listing)
        .where(
            Listing.buyer_id.is_(None), 
            or_(
                and_(
                    Listing.listing_type == 'auction',
                    Listing.end_time > now
                ),
                Listing.listing_type == 'sale'
            )       
        )
        .options(joinedload(Listing.posted_message))
        .order_by(Listing.start_time.desc())
    ) # Сортуємо від нових до старих

    result = await session.execute(query)
    return result.unique().scalars().all()

async def orm_get_or_create_user(session: AsyncSession, user: AiogramUser) -> DbUser:
    db_user = await session.get(DbUser, user.id)

    if db_user:
        # Если пользователь найден и его username изменился, обновляем
        if db_user.username != user.username:
            db_user.username = user.username
            await session.commit()
        return db_user
    
    new_user = DbUser(user_id=user.id, username=user.username)
    session.add(new_user)
    await session.commit()
    return new_user

async def orm_delete_listing(session:AsyncSession, auction_id: int):
    query = delete(Listing).where(Listing.id == auction_id)
    await session.execute(query)
    await session.commit