from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from keyboards.inline import menu_kb
from handlers.menu import get_menu_text

class BaseItemHandler:
    states: None
    start_prompt_text: str = 'Введіть назву:'
    price_promt_text: str = 'Введіть ціну (в €):'

    def __init__(self, bot, session_maker, redis, scheduler):
        self.bot = bot
        self.session_maker = session_maker
        self.redis = redis
        self.scheduler = scheduler

        self.private_router = Router()
        self.private_router.message.filter(F.chat.type == "private")
        self.private_router.callback_query.filter(F.message.chat.type == "private")

        self.public_router = Router()

        self._register_base_handlers()


    async def start_creation(self, callback: CallbackQuery, state: FSMContext):
        await state.clear()
        await callback.message.answer(self.start_prompt_text)
        await callback.answer()
        await state.set_state(self.states.name)

    async def add_name(self, message: Message, state: FSMContext):
        await state.update_data(name=message.text)
        await message.answer('Відправте фото товару:')
        await state.set_state(self.states.photo)

    async def invalid_photo(self, message: Message, state: FSMContext):
        await message.answer('Будь ласка, надішліть фото товару!')
        await state.set_state(self.states.photo)

    async def add_photo(self, message: Message, state: FSMContext):
        if message.photo:
            photo_id = message.photo[-1].file_id
            photo_type = 'photo'
        else:
            photo_id = message.document.file_id
            photo_type = 'document'
        await state.update_data(photo=photo_id, photo_type=photo_type)
        await message.answer('Введіть опис товару:')
        await state.set_state(self.states.description)

    async def add_description(self, message: Message, state: FSMContext):
        await state.update_data(description=message.text)
        await message.answer(self.price_promt_text)
        await state.set_state(self.states.price)

    async def cancel_creation(self, callback: CallbackQuery, state: FSMContext):
        await state.clear()
        await callback.message.delete()
        msg = await callback.message.answer("⚠️ Створення скасовано.")
        await self.bot.send_message(
            chat_id=callback.message.chat.id,
            text=get_menu_text(),
            reply_markup=menu_kb(callback.from_user.id),
            reply_to_message_id=msg.message_id
        )

    def _register_base_handlers(self):  
        # Регистрируем общие шаги
        self.private_router.message.register(self.add_name, F.text, self.states.name)
        self.private_router.message.register(self.invalid_photo, F.text, self.states.photo)
        self.private_router.message.register(self.add_photo, F.photo | (F.document & F.document.mime_type.startswith("image/")), self.states.photo)
        self.private_router.message.register(self.add_description, F.text, self.states.description)

        # Регистрируем общий хендлер отмены
        self.private_router.callback_query.register(self.cancel_creation, F.data == "cancel_lot", self.states.check_state)

    def get_router(self) -> Router:
        self.public_router.include_router(self.private_router)
        return self.public_router