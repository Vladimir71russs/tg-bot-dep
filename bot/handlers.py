import random
from telegram import Update
from telegram.ext import ContextTypes


from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from bot.utils import get_main_menu, get_main_menu_button, get_user
from bot.models import add_word_to_db, delete_word_from_db, get_user_words

# Состояния пользователей для отслеживания режима обучения
user_states = {}

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.message.chat_id
    username = update.message.chat.username or f"User_{telegram_id}"

    user, created = await get_user(telegram_id, username)
    if created:
        # Приветственное сообщение для нового пользователя
        await update.message.reply_text(
            f"Привет, {username}! Добро пожаловать в обучающего бота! 📚\n\n"
            "📖 **Этот бот поможет тебе улучшить знание английского языка.**\n\n"
            "Ты можешь:\n"
            "- Добавлять новые слова и их перевод в свой личный словарь.\n"
            "- Просматривать свой словарь, чтобы не забывать выученные слова.\n"
            "- Удалять ненужные слова.\n"
            "- Начать тренировку, чтобы проверить свои знания.\n\n"
            "🔽 Используй меню ниже, чтобы начать!",
            reply_markup=get_main_menu()
        )
    else:
        # Приветствие для уже зарегистрированного пользователя
        await update.message.reply_text(
            f"Привет, {username}! Добро пожаловать в обучающего бота! 📚\n\n"
            "📖 **Этот бот поможет тебе улучшить знание английского языка.**\n\n"
            "Ты можешь:\n"
            "- Добавлять новые слова и их перевод в свой личный словарь.\n"
            "- Просматривать свой словарь, чтобы не забывать выученные слова.\n"
            "- Удалять ненужные слова.\n"
            "- Начать тренировку, чтобы проверить свои знания.\n\n"
            "🔽 Используй меню ниже, чтобы начать!",
            reply_markup=get_main_menu())


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "main_menu":
        user_states.pop(query.message.chat_id, None)
        await query.message.reply_text("Главное меню:", reply_markup=get_main_menu())

    elif query.data == "learn_words":
        await start_learning(update, context)

    elif query.data == "add_word":
        user_states[query.message.chat_id] = {"state": "adding"}
        await query.message.reply_text("Введите слово в формате 'английское - русский - транскрипция':", reply_markup=get_main_menu_button())

    elif query.data == "my_words":
        words = await get_user_words(query.message.chat_id)
        if words:
            word_list = "\n".join([
                f"{w.english_word} - {w.russian_word}" + (f" - {w.transcription}" if w.transcription else "")
                for w in words
            ])
            total_words = len(words)
            await query.message.reply_text(
                f"Ваш словарь:\n{word_list}\n\n📊 Всего слов в словаре: {total_words}",
                reply_markup=get_main_menu()
            )
        else:
            await query.message.reply_text("Ваш словарь пока пуст.")

    elif query.data == "delete_word":
        user_states[query.message.chat_id] = {"state": "deleting"}
        await query.message.reply_text("Введите слово для удаления (на английском или русском):")

    elif query.data == "finish_learning":  # Новый кейс
        await finish_learning(update, context)

    else:
        await query.message.reply_text("Неизвестная команда.")


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.message.chat_id
    text = update.message.text.strip()

    # Если пользователь в режиме обучения
    if telegram_id in user_states and user_states[telegram_id].get("state") == "learning":
        await continue_learning(update, context)
        return

    # Если пользователь в режиме удаления слов
    if telegram_id in user_states and user_states[telegram_id].get("state") == "deleting":
        await delete_word_from_db(telegram_id, text, update)
        user_states.pop(telegram_id, None)  # Сбрасываем состояние
        return

    # Если пользователь в режиме добавления слова
    if telegram_id in user_states and user_states[telegram_id].get("state") == "adding":
        await add_word_to_db(telegram_id, text, update)
        user_states.pop(telegram_id, None)  # Сбрасываем состояние
        return

    # Если пользователь вводит текст в неизвестном формате
    await update.message.reply_text(
        "Некорректный формат. Выберите действие из меню.",
        reply_markup=get_main_menu()
    )


# Функция, которая начинает обучение
async def start_learning(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from dict.models import Word
    from asgiref.sync import sync_to_async

    telegram_id = update.callback_query.message.chat_id
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

    current_word = words.pop()
    user_states[telegram_id]["current_word"] = current_word

    # Кнопка завершения обучения
    keyboard = [
        [InlineKeyboardButton("Закончить обучение", callback_data="finish_learning")],
        [InlineKeyboardButton("Главное меню", callback_data="main_menu")]
    ]

    # Отправляем сообщение с транскрипцией (если есть)
    message = f"Как переводится слово '{current_word.english_word}'"
    if current_word.transcription:
        message += f" [{current_word.transcription}]"

    await update.callback_query.message.reply_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def finish_learning(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Определяем telegram_id из callback_query
    if update.callback_query:
        telegram_id = update.callback_query.message.chat_id
    else:
        telegram_id = update.message.chat_id

    # Удаляем состояние пользователя
    user_state = user_states.pop(telegram_id, None)

    # Если пользователь не был в режиме обучения
    if not user_state or user_state.get("state") != "learning":
        await update.callback_query.message.reply_text(
            "Вы не находились в режиме обучения.",
            reply_markup=get_main_menu_button()
        )
        return

    # Итоговая статистика
    correct = user_state["correct"]
    incorrect = user_state["incorrect"]
    incorrect_pairs = user_state["incorrect_pairs"]

    # Формируем сообщение с результатами
    result_message = f"Обучение завершено!\n\n"
    result_message += f"✅ Правильных ответов: {correct}\n"
    result_message += f"❌ Неправильных ответов: {incorrect}\n\n"

    if incorrect_pairs:
        result_message += "Ошибки (правильные переводы):\n"
        for eng, correct_translation in incorrect_pairs:
            result_message += f"- {eng} → {correct_translation}\n"

    # Отправляем результаты
    await update.callback_query.message.reply_text(
        result_message,
        reply_markup=get_main_menu()
    )


async def continue_learning(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.message.chat_id
    user_state = user_states.get(telegram_id)

    if not user_state or user_state.get("state") != "learning":
        await update.message.reply_text("Вы не находитесь в режиме обучения.",
                                        reply_markup=get_main_menu_button())
        return

    current_word = user_state["current_word"]
    user_answer = update.message.text.strip().lower()

    # Проверяем правильность ответа
    if user_answer == current_word.russian_word.lower():
        user_state["correct"] += 1
        await update.message.reply_text("Верно! 🎉")
    else:
        user_state["incorrect"] += 1
        # Сохраняем пару (английское слово, правильный перевод)
        user_state["incorrect_pairs"].append((current_word.english_word, current_word.russian_word))
        await update.message.reply_text(
            f"Неправильный перевод слова '{current_word.english_word}'. Правильный ответ: '{current_word.russian_word}'."
        )

    # Выводим текущую статистику
    correct = user_state["correct"]
    incorrect = user_state["incorrect"]
    await update.message.reply_text(f"Переведено правильно: {correct}, неправильно: {incorrect}.")

    # Переходим к следующему слову
    if user_state["words"]:
        next_word = user_state["words"].pop(0)
        user_state["current_word"] = next_word

        message = f"Как переводится слово '{next_word.english_word}'"
        if next_word.transcription:
            message += f" [{next_word.transcription}]"

        await update.message.reply_text(message)
    else:
        # Если все слова выучены
        await finish_learning(update, context)
