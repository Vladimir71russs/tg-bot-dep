from asgiref.sync import sync_to_async
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from dict.models import User

def get_main_menu_button():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Главное меню", callback_data="main_menu")]
    ])


def get_main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Добавить слово", callback_data="add_word")],
        [InlineKeyboardButton("Показать словарь", callback_data="my_words")],
        [InlineKeyboardButton("Учимся", callback_data="learn_words")],
        [InlineKeyboardButton("Удалить слово", callback_data="delete_word")],
    ])

async def get_user(telegram_id, username=None):
    return await sync_to_async(User.objects.get_or_create)(
        telegram_id=telegram_id,
        defaults={"username": username}
    )
