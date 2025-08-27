from typing import Optional

from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from create_bot import admins
from states.states import AdminStates
from keyboards.inline import back_button_kb

from database.models import User

admin_router = Router()
admin_router.message.filter(F.from_user.id.in_(admins))
admin_router.callback_query.filter(F.from_user.id.in_(admins))

@admin_router.callback_query(F.data == 'admin_panel')
async def admin_start(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("Ласкаво просимо в адмін-панель.\nВведіть ID користувача для перевірки:")
    await callback.answer()
    await state.set_state(AdminStates.get_user_id)

@admin_router.message(AdminStates.get_user_id)
async def get_user_id(message: Message, state: FSMContext, session: AsyncSession):
    if not message.text.isdigit():
        await message.answer("ID повинен бути числом. Спробуйте ще раз.")
        return
    
    user_id_to_check = int(message.text)

    user_stmt = await session.execute(select(User).where(User.user_id == user_id_to_check))
    user: Optional[User] = user_stmt.scalar_one_or_none()

    await state.clear()

    if not user:
        await message.answer(f"Користувач з ID `{user_id_to_check}` не знайдений у базі даних.")
        return 
    
    if user.is_banned:
        await message.answer(
            f"<b>Користувач заблокований.</b>\n\n"
            f'ID: "{user.user_id}"\n'
            f"Username: @{user.username if user.username else 'не вказано'}\n"
            f"Попереджень: {user.warnings_count}"
        )
        return
    
    keyboard = InlineKeyboardBuilder()
    keyboard.add(InlineKeyboardButton(text = "Видати попередження 👮",
                                      callback_data=f"warn_user:{user.user_id}"))
    
    await message.answer(f"<b>Знайдено користувача:</b>\n\n"
        f"ID: `{user.user_id}`\n"
        f"Username: @{user.username if user.username else 'не вказано'}\n"
        f"Попереджень: {user.warnings_count}",
        reply_markup=keyboard.as_markup())
    
@admin_router.callback_query(F.data.startswith("warn_user:"))
async def warn_user(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    user_id_to_warn = int(callback.data.split(":")[1])

    user_stmt = await session.execute(select(User).where(User.user_id == user_id_to_warn))
    user: Optional[User] = user_stmt.scalar_one_or_none()

    if not user:
        await callback.answer("Користувач не знайдений!", show_alert=True)
        await callback.message.edit_text("Не вдалося знайти користувача для видачі попередження.")
        return

    user.warnings_count +=1

    ban_message =""
    if user.warnings_count >= 3:
        user.is_banned = True
        ban_message = "\n\n<b>Користувач отримав 3 попередження і був заблокований!</b>"

        try:
            await bot.send_message(user.user_id,
                                   "Ви були заблоковані в боті за багаторазові порушення.")
        except Exception as e:
            print(f"Не вдалося повідомити користувача {user.user_id} про бан: {e}")
        
    await session.commit()

    await callback.message.edit_text(text=f"<b>Користувачеві видано попередження.</b>\n\n"
        f"ID: `{user.user_id}`\n"
        f"Username: @{user.username if user.username else 'не вказано'}\n"
        f"Попереджень: {user.warnings_count}"
        f"{ban_message}",
        reply_markup=back_button_kb().as_markup())
    await callback.answer(f"Попередження видано. Всього: {user.warnings_count}")