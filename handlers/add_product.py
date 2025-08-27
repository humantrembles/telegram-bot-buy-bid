from datetime import datetime, timezone
from aiogram import F

from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from keyboards.inline import (auctioning_off_kb, back_to_menu_kb, buy_now_kb)
from database.models import Listing, Group, PostedMessage
from database.orm_query import orm_get_or_create_user
from .utils import create_listing_caption, extract_number
from states.states import AddProduct
from .base_handler import BaseItemHandler

class ProductHandler(BaseItemHandler):
    states = AddProduct
    start_prompt_text = "Введіть назву товару для продажу:"
    price_promt_text = "Введіть ціну (в €):"

    def __init__(self, bot, session_maker, redis, scheduler):
        super().__init__(bot, session_maker, redis, scheduler)
        self._register_handlers()

    async def add_price(self, message: Message, state: FSMContext):
        price = extract_number(message.text)
        if price is None:
            await message.reply('Ціна повинна бути введена цифрами!')
            await state.set_state(self.states.price)
            return
        
        if price <= 0.1:
            await message.reply('Ціна повинна бути більшою за 0.1!')
            await state.set_state(self.states.price)
            return

        await state.update_data(price=price)
        data = await state.get_data()
            
        caption_text = create_listing_caption(data, is_auction=False, is_confirmation=True)
        markup = auctioning_off_kb()

        if data.get('photo_type') == 'photo':
            await message.answer_photo(photo=data["photo"],
                caption=caption_text,
                reply_markup=markup)
        else:
            await message.answer_document(document=data["photo"],
                caption=caption_text,
                reply_markup=markup)
        await state.set_state(self.states.check_state)
    
    async def confirm_creation(self, callback:CallbackQuery, state: FSMContext):
        data = await state.get_data()
        try:
            async with self.session_maker() as session:
                result = await session.execute(select(Group))
                active_groups = result.scalars().all()
                if not active_groups:
                    await callback.message.edit_caption(caption="❌ Не знайдено жодної групи для публікації. Додайте бота в групу.",
                                                        reply_markup=back_to_menu_kb())
                    await state.clear()
                    return
                
                user = await orm_get_or_create_user(session, callback.from_user)
                obj = Listing(creator_user_id=user.user_id,
                              listing_type='sale',
                              lot_name=data['name'],
                              lot_photo=data['photo'],
                              lot_description=data['description'],
                              price=float(data['price']),
                              start_time=datetime.now(timezone.utc))
                session.add(obj)
                await session.flush()
                product_id = obj.id

                for group in active_groups:
                    try:
                        reply_markup = buy_now_kb(float(data['price']), product_id)
                        caption = create_listing_caption(data, is_auction=False, is_confirmation=False)

                        if data.get('photo_type') == 'photo':
                            sent_message = await self.bot.send_photo(chat_id=group.id,
                                photo=data["photo"],
                                caption=caption,
                                reply_markup=reply_markup)
                        else:
                            sent_message = await self.bot.send_document(chat_id=group.id,
                                document=data["photo"],
                                caption=caption,
                                reply_markup=reply_markup)
                            
                        posted_msg_obj = PostedMessage(listing_id=product_id,
                                                       chat_id=sent_message.chat.id,
                                                       message_id=sent_message.message_id)
                        session.add(posted_msg_obj)
                    except Exception as e:
                        print(f"Не вдалося відправити повідомлення в групу {group.id}: {e}")

                await session.commit()

            success_caption = "✅ Товар успішно виставлений на продаж!"
            await callback.message.edit_caption(caption=success_caption,
                                                reply_markup=back_to_menu_kb())
            await callback.answer()
        except Exception as e:
            print(f"Помилка при створенні товару: {e}")
            try:
                await callback.message.edit_caption(caption="❌ Сталася помилка під час створення товару. Спробуйте ще раз.",
                                                    reply_markup=back_to_menu_kb())
            except Exception as edit_error:
                print(f"Не вдалося відредагувати повідомлення: {edit_error}")
            await callback.message.answer("❌ Сталася помилка під час створення товару. Спробуйте ще раз.")
        finally:
            await state.clear()

    async def handle_purchase(self, callback: CallbackQuery):
        product_id = int(callback.data.split(":")[1])
        buyer_user_info = callback.from_user

        product = None
        buyer = None
        seller = None

        async with self.session_maker() as session:
            product = await session.get(Listing, product_id, options=[selectinload(Listing.creator)])

            if not product or product.listing_type != 'sale':
                await callback.answer("❗️ Товар не знайдено.", show_alert=True)
                return
                
            if product.buyer_id:
                await callback.answer("🏃‍♂️ На жаль, хтось вже купив цей товар.", show_alert=True)
                return
                
            if product.creator_user_id == buyer_user_info.id:
                await callback.answer("❗️ Ви не можете купити власний товар.", show_alert=True)
                return

            buyer = await orm_get_or_create_user(session, buyer_user_info)
            seller = product.creator
                
            product.buyer_id = buyer.user_id
            product.last_price = product.price
            product.end_time = datetime.now(timezone.utc)

            await session.commit()

        try:
            buyer_display = f"@{buyer.username}" if buyer.username else buyer.user_id
            final_caption = (f"{callback.message.caption}\n\n"
                             f"✅ <b>ПРОДАНО!</b>\n"
                             f"👤 Покупець: {buyer_display}\n"
                             f"💰 Ціна: <b>{product.price:.2f} €</b>")
            
            await callback.message.edit_caption(caption=final_caption, reply_markup=None)
            await callback.answer("🎉 Вітаємо з покупкою!")

            seller_display = f"@{seller.username}" if seller.username else f"користувачем з ID {seller.user_id}"

            await self.bot.send_message(seller.user_id,
                f"🎉 Вітаємо! Ваш товар «<b>{product.lot_name}</b>» був куплений.\n\n"
                f"👤 Покупець: {buyer_display}\n"
                f"💰 Ціна: <b>{product.last_price:.2f} €</b>\n\n"
                f"Покупець отримав сповіщення та ваші контакти для зв'язку.")

            buyer_message = (f'🎉 Вітаємо з успішною покупкою товару: «<b>{product.lot_name}</b>»!\n\n'
                             f"💶 Вартість: <b>{product.price:.2f} €</b>\n"
                             f"👤 Для завершення угоди зв'яжіться з продавцем: {seller_display}\n\n"
                             f"Дякуємо, що користуєтесь нашим ботом!")
        
            await self.bot.send_message(buyer_user_info.id, buyer_message)

        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                print(f"Помилка під час оновлення повідомлення про продаж: {e}")
        except Exception as e:
            print(f"Невідома помилка під час обробки покупки: {e}")

    def _register_handlers(self):
        self.private_router.callback_query.register(self.start_creation, F.data == 'add_product')

        self.private_router.message.register(self.add_price, F.text, self.states.price)
        self.private_router.callback_query.register(self.confirm_creation, F.data == 'confirm_lot', self.states.check_state)

        self.public_router.callback_query.register(self.handle_purchase, F.data.startswith('buy:'))