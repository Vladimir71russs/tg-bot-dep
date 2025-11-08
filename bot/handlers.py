from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.learning import start_learning, continue_learning, finish_learning, generate_answer_options
from bot.utils import get_main_menu, get_main_menu_button, get_user
from bot.models import add_word_to_db, delete_word_from_db, get_user_words
from bot.state import user_states
from asgiref.sync import sync_to_async
from dict.models import Word
from random import shuffle

MAX_MESSAGE_LENGTH = 4096


def split_message(text, max_length=MAX_MESSAGE_LENGTH):
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.message.chat_id
    username = update.message.chat.username or f"User_{telegram_id}"

    user, created = await get_user(telegram_id, username)
    text = (
        f"Привет, {username}! Добро пожаловать в обучающего бота! 📚\n\n"
        "📖 **Этот бот поможет тебе улучшить знание английского языка.**\n\n"
        "Ты можешь:\n"
        "- Добавлять новые слова и их перевод.\n"
        "- Просматривать свой словарь.\n"
        "- Удалять слова.\n"
        "- Начать тренировку на английском или русском.\n\n"
        "🔽 Используй меню ниже!"
    )
    await update.message.reply_text(text, reply_markup=get_main_menu())


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("answer:"):
        await continue_learning(update, context)
        return

    if query.data == "main_menu":
        user_states.pop(query.message.chat_id, None)
        await query.message.reply_text("Главное меню:", reply_markup=get_main_menu())

    elif query.data == "learn_words":
        await learn_handler(update, context, reverse=False)

    elif query.data == "learn_words_ru":
        await learn_handler(update, context, reverse=True)

    elif query.data == "add_word":
        user_states[query.message.chat_id] = {"state": "adding"}
        categories_info = (
            "Выберите категорию:\n"
            "1: существительные\n"
            "2: глаголы\n"
            "3: прилагательные\n"
            "4: частицы\n"
            "5: словосочетания\n"
            "6: новые слова\n"
        )
        await query.message.reply_text(
            f"{categories_info} Введите слово в формате 'индекс категории - английское - русский - транскрипция':",
            reply_markup=get_main_menu_button()
        )

    elif query.data == "my_words":
        words = await get_user_words(query.message.chat_id)
        if isinstance(words, tuple) and len(words) == 1 and isinstance(words[0], list):
            words = words[0]
        if words:
            word_list = "\n".join([
                f"{w.english_word} - {w.russian_word}" + (
                    f" - {w.transcription}" if w.transcription else ""
                ) + f" - {w.category}"
                for w in words
            ])
            total_words = len(words)
            for part in split_message(f"Ваш словарь:\n{word_list}\n\n📊 Всего слов: {total_words}"):
                await query.message.reply_text(part, reply_markup=get_main_menu())
        else:
            await query.message.reply_text("Ваш словарь пока пуст.")

    elif query.data == "delete_word":
        user_states[query.message.chat_id] = {"state": "deleting"}
        await query.message.reply_text("Введите слово для удаления:")

    elif query.data == "finish_learning":
        keyboard = [
            [
                InlineKeyboardButton("✅ Закончить", callback_data="confirm_finish_learning"),
                InlineKeyboardButton("🔁 Продолжить", callback_data="continue_learning"),
            ]
        ]
        await query.message.reply_text(
            "Вы действительно хотите закончить обучение?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data == "confirm_finish_learning":
        if not user_states.get(query.message.chat_id):
            await query.message.reply_text(
                "Сессия обучения не найдена.", reply_markup=get_main_menu_button()
            )
            return
        await finish_learning(update, context)

    elif query.data == "continue_learning":
        await query.message.reply_text("Продолжаем обучение 💪")
        await continue_learning(update, context)

    elif query.data == "edit_category":
        user_states[query.message.chat_id] = {"state": "editing"}
        await query.message.reply_text("Введите слово для изменения категории:")

    else:
        await query.message.reply_text("Неизвестная команда.")


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.message.chat_id
    text = update.message.text.strip()

    if telegram_id in user_states and user_states[telegram_id].get("state") == "learning":
        await continue_learning(update, context)
        return

    if telegram_id in user_states and user_states[telegram_id].get("state") == "deleting":
        await delete_word_from_db(telegram_id, text, update)
        user_states.pop(telegram_id, None)
        return

    if telegram_id in user_states and user_states[telegram_id].get("state") == "adding":
        await add_word_to_db(telegram_id, text, update)
        user_states.pop(telegram_id, None)
        return

    await update.message.reply_text("Некорректный формат.", reply_markup=get_main_menu())


def get_category_menu():
    keyboard = [
        [InlineKeyboardButton("Существительные", callback_data="category:существительные")],
        [InlineKeyboardButton("Глаголы", callback_data="category:глаголы")],
        [InlineKeyboardButton("Прилагательные", callback_data="category:прилагательные")],
        [InlineKeyboardButton("Частицы", callback_data="category:частицы")],
        [InlineKeyboardButton("Словосочетания", callback_data="category:словосочетания")],
        [InlineKeyboardButton("Новые слова", callback_data="category:новые слова")],
        [InlineKeyboardButton("Все слова", callback_data="category:все")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def learn_handler(update, context, reverse=False):
    if update.callback_query:
        await update.callback_query.message.reply_text(
            "Выберите категорию для обучения:",
            reply_markup=get_category_menu()
        )
        telegram_id = update.callback_query.from_user.id
    else:
        await update.message.reply_text(
            "Выберите категорию для обучения:",
            reply_markup=get_category_menu()
        )
        telegram_id = update.message.chat_id

    user_states[telegram_id] = {"reverse": reverse}


async def category_handler(update, context):
    query = update.callback_query
    await query.answer()

    callback_data = query.data
    if callback_data.startswith("category:"):
        category = callback_data.split(":", 1)[1]
        telegram_id = query.from_user.id
        reverse_mode = user_states.get(telegram_id, {}).get("reverse", False)

        user_words = await sync_to_async(list)(Word.objects.filter(user__telegram_id=telegram_id))
        if category != "все":
            user_words = [word for word in user_words if word.category == category]

        if not user_words:
            await query.edit_message_text(f"В категории '{category}' пока нет слов.")
            return

        shuffle(user_words)
        user_states[telegram_id] = {
            "state": "learning",
            "reverse": reverse_mode,
            "words": user_words,
            "correct": 0,
            "incorrect": 0,
            "incorrect_pairs": [],
        }

        current_word = user_words[0]
        user_states[telegram_id]["current_word"] = current_word
        random_answers = await generate_answer_options(current_word, reverse=reverse_mode)

        if reverse_mode:
            message = f"Как переводится слово '{current_word.russian_word}'?"
        else:
            message = f"Как переводится слово '{current_word.english_word}'?"

        if current_word.transcription and not reverse_mode:
            message += f" [{current_word.transcription}]"

        keyboard = [
            [InlineKeyboardButton(answer, callback_data=f"answer:{answer}") for answer in random_answers],
            [InlineKeyboardButton("Закончить обучение", callback_data="finish_learning")],
        ]
        await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
