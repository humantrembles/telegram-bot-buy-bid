from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User as AiogramUser

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from database.models import User

class DataBaseSessionMiddleware(BaseMiddleware):
    def __init__(self, session_pool: async_sessionmaker):
        super().__init__()
        self.session_pool = session_pool

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        async with self.session_pool() as session:
            data['session'] = session
            return await handler(event, data)
        
class BanMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user: AiogramUser = data.get('event_from_user')

        if not user or 'session' not in data:
            return await handler(event, data)
        
        session: AsyncSession = data['session']

        db_user = await session.scalar(
            select(User).where(User.user_id == user.id)
        )

        if db_user and db_user.is_banned:
            await event.answer("Ви заблоковані. Подальші питання пишіть розробнику бота.")
            return
    
        return await handler(event, data)
