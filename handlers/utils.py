import re

def extract_number(text):
    match = re.search(r'\b-?\d+(?:\.\d+)?\b', text)
    if match:
        return abs(float(match.group()))
    else:
        return None

def create_listing_caption(data: dict, is_auction: bool = False, is_confirmation: bool = False) -> str:
    caption = (f'📦 <b>Назва товару:</b> {data["name"]}\n'
               f'📝 <b>Опис:</b> {data["description"]}\n'
               f'💶 <b>Стартова ціна:</b> {data["price"]} €\n') 
    if is_auction:
        caption += f'⏳ <b>Тривалість аукціону:</b> {data["duration"]} хв\n'
    if is_confirmation:
        caption += '\n⚠️ <b>Підтвердіть виставлення товару на аукціон:</b>'
    return caption

def key_auc_price(auction_id: int) ->str:
    return f"auction:{auction_id}:start_price"

def key_auc_last_user(auction_id: int) -> str:
    return f"auction:{auction_id}:last_user"

def key_auc_status_msg(auction_id: int) -> str:
    return f"auction:{auction_id}:status_message"

def key_auc_end_time(auction_id: int) -> str:
    return f"auction:{auction_id}:end_time"

def key_auc_info_msg(auction_id: int) -> str:
    return f"auction:{auction_id}:info_message"