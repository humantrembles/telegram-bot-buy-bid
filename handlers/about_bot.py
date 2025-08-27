from aiogram import F, Router
from aiogram.types import CallbackQuery
from keyboards.inline import back_button_kb

about_router = Router()

about_router.message.filter(F.chat.type == "private")
about_router.callback_query.filter(F.message.chat.type == "private")

@about_router.callback_query(F.data == 'about_bot')
async def help_selection_ukr(callback: CallbackQuery):
    await callback.message.edit_text("ℹ️ Проект створений з метою вивчення процесів розробки Telegram-ботів.\n\n"
                                     "Зворотний зв’язок вітається: помилки, ідеї або пропозиції — пишіть @paralysatione!",
                                     reply_markup=back_button_kb().as_markup())
    await callback.answer()