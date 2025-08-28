from datetime import datetime, timedelta, timezone

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from apscheduler.triggers.date import DateTrigger
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .base_handler import BaseItemHandler
from keyboards.inline import (auctioning_off_kb, price_kb,
                              back_to_menu_kb)
from database.models import Listing, User, Group, PostedMessage
from database.orm_query import orm_get_or_create_user
from create_bot import redis
from .utils import (create_listing_caption, extract_number, key_auc_price,
                            key_auc_last_user, key_auc_status_msg, key_auc_end_time,
                            key_auc_info_msg)
from states.states import AddLot

async def _get_time_str(redis_conn, auction_id: int) -> str:
    end_time_raw = await redis_conn.get(key_auc_end_time(auction_id))
    if not end_time_raw:
        return "Невідомо"
    end_time = datetime.fromisoformat(end_time_raw.decode())
    now = datetime.now(timezone.utc)
    remaining = end_time - now
    if remaining.total_seconds() > 0:
        m, s = divmod(int(remaining.total_seconds()), 60)
        return f"До завершення: {m} хв {s} сек"
    else:
        return "🥸"

class AuctionHandler(BaseItemHandler):
    states = AddLot
    start_prompt_text = "Введіть назву аукціонного лота:"
    price_promt_text = "Введіть стартову ціну (в €):"

    def __init__(self, bot, session_maker, redis, scheduler):
        super().__init__(bot, session_maker, redis, scheduler)
        self._register_handlers()

    async def add_price(self, message: Message, state: FSMContext):
        price = extract_number(message.text)
        if price is None:
            await message.reply('Стартова ціна повинна бути введена цифрами!')
            await state.set_state(self.states.price)
            return
        
        if price <= 0.1:
            await message.reply('Стартова ціна повинна бути більшою за 0.1!')
            await state.set_state(self.states.price)
            return

        await state.update_data(price=price)
        await message.answer('Введіть тривалість аукціону (у хвилинах):')
        await state.set_state(self.states.duration)

    async def add_duration(self, message: Message, state: FSMContext):
        duration = extract_number(message.text)
        if not duration or int(duration) < 1:
            await message.reply('Мінімальна тривалість аукціону - 1 хвилина!')
            await state.set_state(self.states.duration)
        else:
            await state.update_data(duration=duration)
            data = await state.get_data()

            caption = create_listing_caption(data, is_auction=True, is_confirmation=True)
            markup = auctioning_off_kb()
            if data.get('photo_type') == 'photo':
                await message.answer_photo(photo=data["photo"],
                                           caption=caption,
                                           reply_markup=markup)
            else:
                await message.answer_document(document=data["photo"],
                                              caption=caption,
                                              reply_markup=markup)
            await state.set_state(self.states.check_state)
    
    async def confirm_creation(self, callback: CallbackQuery, state: FSMContext):
        data = await state.get_data()
        try:
            duration = float(data['duration'])
            start_time = datetime.now(timezone.utc)
            end_time = start_time + timedelta(minutes=duration)
            async with self.session_maker() as session:
                result = await session.execute(select(Group))
                active_groups = result.scalars().all()
                if not active_groups:
                    await callback.message.edit_caption(caption="❌ Не знайдено жодної групи для публікації. Додайте бота в групу.",
                                                        reply_markup=back_to_menu_kb())
                    await state.clear()
                    return
                
                user = await orm_get_or_create_user(session, callback.from_user)
                obj = Listing(creator_user_id = user.user_id,
                    listing_type = 'auction',
                    lot_name = data['name'],
                    lot_photo = data['photo'],
                    lot_description = data['description'],
                    price = float(data['price']),
                    start_time = start_time,
                    end_time = end_time)
                session.add(obj)
                await session.flush()
                auction_id = obj.id 

                print(f"Виконується попереднє очищення для аукціону ID: {auction_id}")
                keys_to_delete = [key_auc_price(auction_id),
                                  key_auc_last_user(auction_id),
                                  key_auc_status_msg(auction_id),
                                  key_auc_end_time(auction_id),
                                  key_auc_info_msg(auction_id)]
                await self.redis.delete(*keys_to_delete)

                for group in active_groups:
                    try:
                        reply_markup = price_kb(float(data['price']), auction_id)
                        caption = create_listing_caption(data, is_auction=True, is_confirmation=False)

                        if data.get('photo_type') == 'photo':
                            sent_message = await self.bot.send_photo(
                                chat_id=group.id,         
                                photo=data["photo"],
                                caption=caption,
                                reply_markup=reply_markup)
                        else:
                            sent_message = await self.bot.send_document(
                                chat_id=group.id,
                                document=data["photo"],
                                caption=create_listing_caption(data, is_auction=True, is_confirmation=False),
                                reply_markup=reply_markup)
                            
                        posted_msg_obj = PostedMessage(listing_id = auction_id,
                                                      chat_id=sent_message.chat.id,
                                                      message_id=sent_message.message_id)
                        session.add(posted_msg_obj)
                    except Exception as e:
                        print(f"Не вдалося відправити повідомлення в групу {group.id}: {e}")

                await session.commit()
            
                await self.redis.set(key_auc_price(auction_id),  float(data['price'])) 
                await self.redis.set(key_auc_end_time(auction_id), end_time.isoformat())
                self.scheduler.add_job(self._finish_auction_job,
                                  trigger=DateTrigger(run_date=end_time),
                                  args=[auction_id],
                                  id=f"finish_auc:{auction_id}")
            success_caption = "✅ Аукціон успішно виставлено!"
            await callback.message.edit_caption(caption=success_caption,
                                                reply_markup=back_to_menu_kb())
            await callback.answer()
        except Exception as e:
            print(f"Помилка при підтвердженні лоту: {e}")
            try:
                await callback.message.edit_caption(caption="❌ Сталася помилка при створенні аукціону. Спробуйте ще раз.",
                                                    reply_markup=back_to_menu_kb())
            except Exception as edit_error:
                print(f"Не вдалося відредагувати повідомлення: {edit_error}")
            await callback.message.answer("❌ Сталася помилка при створенні аукціону. Спробуйте ще раз.")
        finally:
            await state.clear()

    async def _finish_auction_job(self, auction_id: int):
        print(f"Підведення підсумків аукціону {auction_id}...")

        try:
            final_price_raw = await self.redis.get(key_auc_price(auction_id))
            last_user_id_raw = await self.redis.get(key_auc_last_user(auction_id))
            winner_user = None

            async with self.session_maker() as session:
                auction = await session.get(Listing,
                                            auction_id,
                                            options=[selectinload(Listing.creator), selectinload(Listing.posted_message)])
                if not auction or not auction.creator:
                    print(f"Помилка: не знайдено аукціон {auction_id} або його творця в БД")
                    return
        
                seller = auction.creator
                seller_display = f"@{seller.username}" if seller.username else f"користувачем з ID {seller.user_id}"
                
                final_price = float(final_price_raw) if final_price_raw else auction.price
                
                if last_user_id_raw:
                    winner_id = int(last_user_id_raw)
                    try:
                        winner_aiogram_user = await self.bot.get_chat(winner_id)
                        winner_user = await orm_get_or_create_user(session, winner_aiogram_user)     
                        auction.buyer_id = winner_user.user_id
                        auction.last_price = final_price
                    except Exception as e:
                        print(f"Не вдалося отримати дані про переможця {winner_id}: {e}")
                        winner_user = None
                
                if not winner_user:
                    auction.last_price = auction.price

                await session.commit()  

            header = (f'🎁 <b>Назва товару:</b> {auction.lot_name}\n'
                      f'📝 <b>Опис:</b> {auction.lot_description}\n'
                      f'💶 <b>Стартова ціна:</b> {auction.price:.2f} €')
        
            final_status = "Аукціон завершено!"

            if winner_user:
                winner_display = f"@{winner_user.username}" if winner_user.username else f"користувачем з ID {winner_user.user_id}"
                final_result = f"Переможець: {winner_display}, остаточна ціна: <b>{final_price:.2f} €</b>"
                # 1. Надсилаємо сповіщення продавцю про успішний продаж
                seller_message = (f"🎉 Вітаємо! Ваш аукціон на лот «<b>{auction.lot_name}</b>» завершено!\n\n"
                                  f"👤 Переможець: {winner_display}\n"
                                  f"💰 Фінальна ціна: <b>{final_price:.2f} €</b>\n\n"
                                  f"Переможець отримав сповіщення та ваші контакти для зв'язку.")
                # 2. Надсилаємо сповіщення переможцю з контактами продавця
                winner_message = (f"🎉 Вітаємо! Ви перемогли в аукціоні й виграли лот з назвою «<b>{auction.lot_name}</b>»!\n\n"
                                  f"💰 Виграшна ставка: <b>{final_price:.2f} €</b>\n"
                                  f"👤 Для завершення угоди зв'яжіться з продавцем: {seller_display}\n\n"
                                  f"Дякуємо, що користуєтесь нашим ботом!")
                try:
                    await self.bot.send_message(winner_user.user_id, winner_message)
                except TelegramForbiddenError:
                    print(f"Не вдалося надіслати повідомлення переможцю {winner_user.user_id}. Користувач заблокував бота.")
                    seller_message += "\n\n❗️<b>Важливо:</b> не вдалося надіслати сповіщення переможцю. Схоже, він не починав діалогу з ботом або заблокував."
                try:
                    await self.bot.send_message(seller.user_id, seller_message)
                except TelegramForbiddenError:
                    print(f"Не вдалося надіслати повідомлення продавцю {seller.user_id}. Користувач заблокував бота.")
            else:
                final_result = "На жаль, не було зроблено жодної ставки."
                seller_message_no_bids = (f"😔 На жаль, ваш аукціон на лот «<b>{auction.lot_name}</b>» завершився без жодної ставки.")
                try:
                    await self.bot.send_message(seller.user_id, seller_message_no_bids)
                except TelegramForbiddenError:
                    print(f"Не вдалося надіслати повідомлення продавцю {seller.user_id} про відсутність ставок. Користувач заблокував бота.")

            final_block = (f"\n\n🏁<b>ПІДСУМКИ!</b>\n"
                           f"<b>Статус:</b> {final_status}\n"
                           f"<b>Результат:</b> {final_result}")
            full_final_caption = header + final_block

            for posted_msg in auction.posted_message:
                try:
                    await self.bot.edit_message_caption(chat_id=posted_msg.chat_id,
                                           message_id=posted_msg.message_id,
                                           caption=full_final_caption,
                                           reply_markup=None)
                except Exception as e:
                    print(f"Не вдалося оновити повідомлення {posted_msg.message_id} в чаті {posted_msg.chat_id}: {e}")

            status_msg_info = await redis.hgetall(key_auc_status_msg(auction_id))
            if status_msg_info:
                try:
                    await self.bot.delete_message(chat_id=int(status_msg_info[b"chat_id"]),
                        message_id=int(status_msg_info[b"message_id"]))
                except Exception as e:
                    print(f"Не вдалося видалити статусне повідомлення: {e}")
        
        except Exception as e:
            print(f"Глобальна помилка в _finish_auction_job для аукціону {auction_id}: {e}")
        finally:
            print(f"Очищення даних Redis для аукціону {auction_id}...")
            keys_to_delete = [key_auc_price(auction_id),
                              key_auc_last_user(auction_id),
                              key_auc_status_msg(auction_id),
                              key_auc_end_time(auction_id),
                              key_auc_info_msg(auction_id)]
            if await self.redis.exists(*keys_to_delete):
                await self.redis.delete(*keys_to_delete)
            print(f"Дані для аукціону {auction_id} очищено.")


    async def increase_bid(self, callback: CallbackQuery):
        auction_id = int(callback.data.split(":")[1])  
        user_info = callback.from_user

        price_raw = await self.redis.get(key_auc_price(auction_id))
        if price_raw is None:
            await callback.answer("❗️ Аукціон вже завершено.", show_alert=True)
            try:
                await callback.message.edit_reply_markup(reply_markup=None)
            except TelegramBadRequest:
                pass
            return

        async with self.session_maker() as session:
            auction = await session.get(Listing, auction_id)
            if not auction:
                await callback.answer("❗️ Аукціон не знайдено, можливо, він завершився.", show_alert=True)
                return
    
        if auction.creator_user_id == user_info.id:
            await callback.answer("❗️ Ви не можете робити ставку на власний лот.", show_alert=True)
            return

        last_user_id_raw = await self.redis.get(key_auc_last_user(auction_id))
        if last_user_id_raw and int(last_user_id_raw.decode()) == user_info.id:
            await callback.answer('Ви вже зробили ставку.')
            return

        current_price = float(price_raw)
        bid_increment = 0.05 if current_price < 1  else (0.1 if current_price < 10 else 0.25)
    
        new_price_raw = await self.redis.incrbyfloat(key_auc_price(auction_id), bid_increment)
        new_price = round(float(new_price_raw), 2)
    
        await self.redis.set(key_auc_last_user(auction_id), user_info.id)

        user_display = f"@{user_info.username}" if user_info.username else user_info.first_name

        new_markup = price_kb(new_price, auction_id)
        await callback.message.edit_reply_markup(reply_markup=new_markup)

        time_str = await _get_time_str(self.redis, auction_id)
        text = f'{user_display} зробив ставку: <b>{new_price:.2f} €</b>. {time_str}'

        status_msg_info = await self.redis.hgetall(key_auc_status_msg(auction_id))

        try:
            if not status_msg_info:
                sent_message = await callback.message.reply(text)
                await self.redis.hset(key_auc_status_msg(auction_id), mapping={
                    "message_id": sent_message.message_id,
                    "chat_id": sent_message.chat.id})
            else:
                await self.bot.edit_message_text(chat_id=int(status_msg_info[b"chat_id"]),
                                                             message_id=int(status_msg_info[b"message_id"]),
                                                             text=text)
        except TelegramBadRequest as e:
                if "message is not modified" not in str(e):
                    print(f"Помилка при оновленні status_message: {e}")
        await callback.answer()

    def _register_handlers(self):
        # Регистрируем приватные хендлеры на private_router из базового класса
        self.private_router.callback_query.register(self.start_creation, F.data == 'add_lot')
        
        # Регистрируем уникальные хендлеры для аукциона
        self.private_router.message.register(self.add_price, F.text, self.states.price)
        self.private_router.message.register(self.add_duration, F.text, self.states.duration)
        self.private_router.callback_query.register(self.confirm_creation, F.data == 'confirm_lot', self.states.check_state)
        
        #Регистрируем публичный хендлер на public_router из базового класса
        self.public_router.callback_query.register(self.increase_bid, F.data.startswith('bid:'))