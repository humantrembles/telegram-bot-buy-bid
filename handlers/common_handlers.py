from aiogram import F, Router, Bot
from aiogram.types import Message, CallbackQuery

from keyboards.inline import menu_kb
from .menu import get_menu_text
from database.models import Group
from create_bot import session_maker, admins

common_router = Router()

@common_router.message(F.new_chat_members)
async def bot_added_to_group(message: Message, bot: Bot):
    for member in message.new_chat_members:
        if member.id == bot.id:
            inviter_id = message.from_user.id
            chat_id = message.chat.id

            if inviter_id not in admins:
                await bot.send_message(chat_id,
                                       "🚫 Лише власник бота може запрошувати мене у нові чати.")
                await bot.leave_chat(chat_id)
                return  

            async with session_maker() as session:
                group = await session.get(Group, chat_id)
                if not group:
                    session.add(Group(id=chat_id, title=message.chat.title))
                    await session.commit()
                    print(f"Бот доданий до нової групи: {message.chat.title} (ID: {chat_id})")

            welcome_text = ("👋 <b>Вітаю всіх!</b>\n\n"
                "Я ваш бот-помічник для організації продажів та аукціонів.\n\n"
                "<b>Що я вмію:</b>\n"
                "✅ Створювати та проводити аукціони.\n"
                "✅ Допомагати продавати та купувати товари.\n\n"
                "Щоб розпочати, переходь в особисті повідомлення і пиши команду /start.")
            
            await bot.send_message(chat_id, welcome_text)
            break

@common_router.message(F.left_chat_member)
async def bot_left_group(message: Message, bot: Bot):
    if message.left_chat_member.id == bot.id:
        chat_id = message.chat.id

        async with session_maker() as session:
            group = await session.get(Group, chat_id)
            if group:
                await session.delete(group)
                await session.commit()
                print(f"Бот був видалений з групи: {message.chat.title} (ID: {chat_id})")