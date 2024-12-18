import random
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from asgiref.sync import sync_to_async

from bot.utils import get_main_menu_button, get_main_menu, get_user
from bot.state import user_states
from dict.models import Word

# Состояния пользователей


async def start_learning(update, context):
    telegram_id = update.callback_query.message.chat_id
    print(f"[DEBUG] start_learning: Current user state before: {user_states.get(telegram_id)}")

    # Остальная логика функции
    user, _ = await get_user(telegram_id)
    words = await sync_to_async(list)(Word.objects.filter(user_id=user.id))

    if not words:
        await update.callback_query.message.reply_text(
            "Ваш словарь пуст. Добавьте слова для начала обучения.",
            reply_markup=get_main_menu_button()
        )
        return

    random.shuffle(words)
    user_states[telegram_id] = {
        "state": "learning",
        "words": words,
        "correct": 0,
        "incorrect": 0,
        "incorrect_pairs": []
    }
    print(f"[DEBUG] start_learning: Current user state after: {user_states.get(telegram_id)}")

    current_word = words.pop()
    user_states[telegram_id]["current_word"] = current_word
    message = f"Как переводится слово '{current_word.english_word}'"
    if current_word.transcription:
        message += f" [{current_word.transcription}]"

    keyboard = [
        [InlineKeyboardButton("Закончить обучение", callback_data="finish_learning")],
        [InlineKeyboardButton("Главное меню", callback_data="main_menu")]
    ]
    await update.callback_query.message.reply_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def continue_learning(update, context):
    telegram_id = update.message.chat_id
    print(f"[DEBUG] continue_learning: Current user state: {user_states.get(telegram_id)}")

    user_state = user_states.get(telegram_id)
    if not user_state or user_state.get("state") != "learning":
        await update.message.reply_text(
            "Вы не находитесь в режиме обучения.",
            reply_markup=get_main_menu_button()
        )
        return

    # Проверяем ответ пользователя
    current_word = user_state["current_word"]
    user_answer = update.message.text.strip().lower()

    if user_answer == current_word.russian_word.lower():
        user_state["correct"] += 1
        await update.message.reply_text("Верно! 🎉")
    else:
        user_state["incorrect"] += 1
        user_state["incorrect_pairs"].append((current_word.english_word, current_word.russian_word))
        await update.message.reply_text(
            f"Неправильный перевод слова '{current_word.english_word}'. Правильный ответ: '{current_word.russian_word}'."
        )

    # Проверяем, есть ли ещё слова
    if user_state["words"]:
        # Берём следующее слово
        current_word = user_state["words"].pop()
        user_state["current_word"] = current_word

        message = f"Как переводится слово '{current_word.english_word}'"
        if current_word.transcription:
            message += f" [{current_word.transcription}]"

        keyboard = [
            [InlineKeyboardButton("Закончить обучение", callback_data="finish_learning")],
            [InlineKeyboardButton("Главное меню", callback_data="main_menu")]
        ]
        await update.message.reply_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        # Если слова закончились, вызываем finish_learning
        await finish_learning(update, context)

async def finish_learning(update, context):
    telegram_id = update.callback_query.message.chat_id if update.callback_query else update.message.chat_id
    user_state = user_states.pop(telegram_id, None)
    print(f"[DEBUG] finish_learning: User state after pop: {user_state}")

    if not user_state or user_state.get("state") != "learning":
        if update.callback_query:
            await update.callback_query.message.reply_text(
                "Вы не находились в режиме обучения.",
                reply_markup=get_main_menu_button()
            )
        else:
            await update.message.reply_text(
                "Вы не находились в режиме обучения.",
                reply_markup=get_main_menu_button()
            )
        return

    correct = user_state["correct"]
    incorrect = user_state["incorrect"]
    incorrect_pairs = user_state["incorrect_pairs"]

    result_message = f"Обучение завершено!\n\n"
    result_message += f"✅ Правильных ответов: {correct}\n"
    result_message += f"❌ Неправильных ответов: {incorrect}\n\n"

    if incorrect_pairs:
        result_message += "Ошибки (правильные переводы):\n"
        for eng, correct_translation in incorrect_pairs:
            result_message += f"- {eng} → {correct_translation}\n"

    if update.callback_query:
        await update.callback_query.message.reply_text(
            result_message,
            reply_markup=get_main_menu()
        )
    else:
        await update.message.reply_text(
            result_message,
            reply_markup=get_main_menu()
        )

