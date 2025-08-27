from aiogram import F, Router
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_query import orm_get_active_listings
from keyboards.inline import back_button_kb

offers_router = Router()

offers_router.message.filter(F.chat.type == "private")
offers_router.callback_query.filter(F.message.chat.type == "private")

@offers_router.callback_query(F.data == 'offers')
async def show_active_listings(callback: CallbackQuery, session: AsyncSession):
    active_listings = await orm_get_active_listings(session)

    if not active_listings:
        await callback.message.edit_text("😔 Активних лотів наразі немає.",
                                         reply_markup=back_button_kb().as_markup())
        await callback.answer()
        return
    
    keyboard = InlineKeyboardBuilder()
    text = "<b>✨ Ось список активних лотів:</b>\n\n"

    for listing in active_listings:
        for post in listing.posted_message:
            if not post.message_id or not post.chat_id:
                continue
           
            chat_id_for_url = str(post.chat_id)[4:] # Removes the "-100" prefix
            url = f"https://t.me/c/{chat_id_for_url}/{post.message_id}"
            listing_emoji = "🎁 Лот" if listing.listing_type == 'auction' else "📦 Товар"
            price = round(float(listing.price), 2)
            button_text = f"{listing_emoji} {listing.lot_name} | {price} €"

            keyboard.button(text=button_text, url=url)
            #break на случай если будет два и более чатов
    
    if not keyboard.buttons:
        await callback.message.edit_text("😔 Не вдалося знайти посилання на активні лоти.",
                                         reply_markup=back_button_kb().as_markup())
        await callback.answer()
        return

    keyboard.attach(back_button_kb())
    keyboard.adjust(1)

    await callback.message.edit_text(text, reply_markup=keyboard.as_markup())
    await callback.answer()    
