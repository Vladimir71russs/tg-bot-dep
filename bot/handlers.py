from telegram import Update
from telegram.ext import ContextTypes

from bot.learning import start_learning, continue_learning, finish_learning
from bot.utils import get_main_menu, get_main_menu_button, get_user
from bot.models import add_word_to_db, delete_word_from_db, get_user_words
from bot.state import user_states
# Состояния пользователей для отслеживания режима обучения


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