from aiogram.types import (InlineKeyboardMarkup, InlineKeyboardButton)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from create_bot import admins

'''def language_kb() -> InlineKeyboardMarkup: # варіант для багаторівневого меню
    buttons = [[InlineKeyboardButton(text='🇺🇦 UKR', callback_data='ukr'),
                InlineKeyboardButton(text='🇺🇸 ENG', callback_data='eng')]]
    return InlineKeyboardMarkup(inline_keyboard=buttons)'''

def menu_kb(user_telegram_id: int) -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(text='💎 Активні пропозиції', callback_data='offers')],
                [InlineKeyboardButton(text='➕ Додати лот', callback_data='add_lot'),
                InlineKeyboardButton(text="💼 Додати товар", callback_data='add_product')],
                [InlineKeyboardButton(text='ℹ️ Про бота', callback_data='about_bot')]]
                #,InlineKeyboardButton(text='🔙 Назад', callback_data='back_to_lang_kb')]]
    if user_telegram_id in admins:
        buttons.append([InlineKeyboardButton(text='⚙️ Панель адміна', callback_data='admin_panel')])
    return InlineKeyboardMarkup(inline_keyboard=buttons, resize_keyboard=True)

def auctioning_off_kb() -> InlineKeyboardMarkup:
    buttons =[[InlineKeyboardButton(text='✅ Виставляємо', callback_data='confirm_lot')],
              [InlineKeyboardButton(text='❌ Відміняємо', callback_data='cancel_lot')]]
    return InlineKeyboardMarkup(inline_keyboard=buttons) 

def price_kb(price: float, auction_id: int) -> InlineKeyboardMarkup:
    button = [[InlineKeyboardButton(text=f'💰 Поточна ставка: {price:.2f} €' , callback_data= f"bid:{auction_id}" )]]
    return InlineKeyboardMarkup(inline_keyboard=button)

def buy_now_kb(price: float, product_id: int) -> InlineKeyboardMarkup:
    button = [[InlineKeyboardButton(text=f"🛒 Купити за {price} €", callback_data=f"buy:{product_id}")]]
    return InlineKeyboardMarkup(inline_keyboard=button)

def back_to_menu_kb()-> InlineKeyboardMarkup:
    button = [[InlineKeyboardButton(text="⬅️ Повернутись в меню", callback_data="back_to_menu_button")]]
    return InlineKeyboardMarkup(inline_keyboard=button)

def back_button_kb() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад", callback_data='back_to_menu_builder')
    return builder