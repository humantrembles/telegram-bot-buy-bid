from aiogram.fsm.state import State, StatesGroup

class AddLot(StatesGroup):
    name = State()
    photo = State()
    description = State()
    price = State()
    duration = State()
    check_state = State()

class AddProduct(StatesGroup):
    name = State()
    photo = State()
    description = State()
    price = State()
    check_state = State()

class AdminStates(StatesGroup):
    get_user_id = State()