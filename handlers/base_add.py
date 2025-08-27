from aiogram import Router, F
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from handlers.utils import extract_number

base_router = Router()

class BaseAdd(StatesGroup):
    name = State()
    photo = State()
    description = State()
    price = State()
    check_state = State()

@base_router.message(F.text, BaseAdd.name)
async def add_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer('Відправте фото товару:')
    await state.set_state(BaseAdd.photo)

@base_router.message(F.text, BaseAdd.photo)
async def invalid_photo(message: Message, state: FSMContext):
    await message.answer('Будь ласка, надішліть фото товару!')
    await state.set_state(BaseAdd.photo)

@base_router.message(F.photo | (F.document & F.document.mime_type.startswith("image/")), BaseAdd.photo)
async def add_photo(message: Message, state: FSMContext):
    if message.photo:
        photo_id = message.photo[-1].file_id 
        photo_type='photo'
    else:
        photo_id = message.document.file_id
        photo_type='document'
    await state.update_data(photo=photo_id, photo_type=photo_type)
    await message.answer('Введіть опис товару:')
    await state.set_state(BaseAdd.description)

@base_router.message(F.text, BaseAdd.description)
async def add_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer('Введіть ціну (в €):')
    await state.set_state(BaseAdd.price)
    
@base_router.message(F.text, BaseAdd.price)
async def add_price(message: Message, state: FSMContext):
    price = extract_number(message.text)
    if not price:
        await message.reply('Ціна повинна бути введена цифрами!')
        await state.set_state(BaseAdd.price)
    else:
        await state.update_data(price=price)
        await message.answer('Введіть тривалість аукціону (у хвилинах):')
        await state.set_state(BaseAdd.duration)
