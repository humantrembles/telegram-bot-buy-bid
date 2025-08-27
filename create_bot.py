from redis.asyncio import Redis
from decouple import config
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from database.models import Base

ADMINS = config("ADMINS")
TOKEN = config("TOKEN")
#GROUP_ID = config("GROUP_ID")

admins = [int(admin_id) for admin_id in config('ADMINS').split(',')]

redis_url = config('REDIS_URL')
storage = RedisStorage.from_url(redis_url)

engine = create_async_engine(config('PG_LINK'))
session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

redis = Redis.from_url(redis_url)

bot = Bot(token=config('TOKEN'), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=storage)

scheduler = AsyncIOScheduler()

async def create_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def drop_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

async def check_redis_connection():
     try:
          info = await redis.info()
          print(info['redis_version'])
          if await redis.ping():
               print("Подключение успешно!")
          else:
               print("Не удалось подключиться к Redis.")
     except Exception as e:
          print(f"Ошибка Redis: {e}")