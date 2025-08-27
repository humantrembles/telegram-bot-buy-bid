import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, BotCommandScopeAllPrivateChats, BotCommandScopeAllGroupChats

from create_bot import bot, dp, session_maker, scheduler, redis, ADMINS, drop_db, create_db, check_redis_connection
from handlers import menu, offers, add_lot, add_product, about_bot, common_handlers, admin_panel
from middlewares.db import DataBaseSessionMiddleware, BanMiddleware

async def set_bot_commands(bot: Bot):
    private_commands = [BotCommand(command='start', description='Старт')]
    await bot.set_my_commands(private_commands, BotCommandScopeAllPrivateChats())
    await bot.set_my_commands([], BotCommandScopeAllGroupChats())

async def on_startup(bot: Bot) -> None:
    await set_bot_commands(bot)
    await create_db()
    await check_redis_connection()
    await bot.delete_webhook(drop_pending_updates=True)
    scheduler.start()
    await bot.send_message(chat_id=ADMINS, text='Bot started!')   
    print('Bot started!') 

async def on_shutdown(bot: Bot) -> None:
    print('Bot stopping...')
    scheduler.shutdown(wait=False)
    await dp.storage.close() # 3. Закрываем соединение Redis FSM
    await redis.aclose() # 4. Закрываем ваше второе соединение Redis
    await bot.session.close()
    await bot.send_message(chat_id=ADMINS, text='Bot stopped!')
    print('Bot stopped!')

def register_all_handlers(dp):
    auction_handler = add_lot.AuctionHandler(bot, session_maker, redis, scheduler)
    product_handler = add_product.ProductHandler(bot, session_maker, redis, scheduler)

    dp.include_router(menu.menu_router)
    dp.include_router(offers.offers_router)
    dp.include_router(auction_handler.get_router())
    dp.include_router(product_handler.get_router())
    dp.include_router(about_bot.about_router)
    dp.include_router(admin_panel.admin_router)
    dp.include_router(common_handlers.common_router)

async def main() -> None:
    dp.update.outer_middleware.register(DataBaseSessionMiddleware(session_pool=session_maker))
    dp.update.outer_middleware.register(BanMiddleware())

    register_all_handlers(dp)
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    await dp.start_polling(bot)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    asyncio.run(main())