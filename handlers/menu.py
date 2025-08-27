from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery

from keyboards.inline import menu_kb#, language_kb, back_button_kb

menu_router = Router()

menu_router.message.filter(F.chat.type == "private")
menu_router.callback_query.filter(F.message.chat.type == "private")

def get_start_text() -> str:
    return 'Choose your language'

def get_menu_text() -> str:
    #return 'Ось меню для українців 👇' варіант для багаторівневого меню
    return 'Ось головне меню 👇'

@menu_router.message(CommandStart())
async def start(message: Message):
    '''telegram_id = message.from_user.id
    user_data = await get_user_by_id(telegram_id)
    if user_data is None:
        user = await add_user(telegram_id=telegram_id,
                       username=message.from_user.username,
                       first_name=message.from_user.first_name)
        return user'''
    #await message.answer(text=get_start_text(), reply_markup=language_kb()) варіант для багаторівневого меню
    await message.answer(text=get_menu_text(), reply_markup=menu_kb(message.from_user.id))

'''@menu_router.callback_query(F.data == 'ukr') # варіант для багаторівневого меню
async def language_selection_ukr(callback: CallbackQuery):
    await callback.message.edit_text(text=get_menu_text(),
                                     reply_markup=menu_kb(callback.from_user.id))
    await callback.answer()
    
@menu_router.callback_query(F.data == 'eng')
async def english(callback: CallbackQuery):
    await callback.message.edit_text(text="♿️♿️♿️", 
        reply_markup=back_button_kb().as_markup())
    await callback.answer()

@menu_router.callback_query(F.data == 'back_to_lang_kb')
async def back_to_language_kb(callback: CallbackQuery):
    await callback.message.edit_text(text=get_start_text(), reply_markup=language_kb())
    await callback.answer()'''

@menu_router.callback_query(F.data == 'back_to_menu_builder')
async def back_to_menu_builder(callback: CallbackQuery):
    await callback.message.edit_text(text=get_menu_text(), reply_markup=menu_kb(callback.from_user.id))
    await callback.answer()

@menu_router.callback_query(F.data == 'back_to_menu_button')
async def back_to_menu_kb_new_msg(callback:CallbackQuery):
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(text=get_menu_text(), reply_markup=menu_kb(callback.from_user.id))
    await callback.answer()

'''@start_router.message(F.new_chat_members) # ЭТО на будущее, если захочу масштабировать бота для других телеграмм чатов
async def bot_added_to_group(message: Message):
    for member in message.new_chat_members:
        if member.id == message.bot.id:
            chat_id = message.chat.id
            chat_title = message.chat.title
            await message.answer(f'Бота додано в чат: {chat_title} (ID: {chat_id})')'''
