from telegram import Update
from telegram.ext import ContextTypes
from bot.learning import start_learning, continue_learning, finish_learning, generate_answer_options
from bot.utils import get_main_menu, get_main_menu_button, get_user
from bot.models import add_word_to_db, delete_word_from_db, get_user_words
from bot.state import user_states
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from asgiref.sync import sync_to_async
from dict.models import Word
from random import shuffle


MAX_MESSAGE_LENGTH = 4096  # Максимальная длина сообщения Telegram

def split_message(text, max_length=MAX_MESSAGE_LENGTH):
    """Разбивает сообщение на части, если оно слишком длинное."""
    return [text[i:i+max_length] for i in range(0, len(text), max_length)]


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

    # Если нажата кнопка с ответом
    if query.data.startswith("answer:"):
        await continue_learning(update, context)
        return

    if query.data == "main_menu":
        user_states.pop(query.message.chat_id, None)
        await query.message.reply_text("Главное меню:", reply_markup=get_main_menu())

    elif query.data == "learn_words":
        await learn_handler(update, context)

    elif query.data == "add_word":
        user_states[query.message.chat_id] = {"state": "adding"}
        categories_info = (
            "Выберите категорию, указав соответствующую цифру:\n"
            "1: существительные\n"
            "2: глаголы\n"
            "3: прилагательные\n"
            "4: частицы\n"
            "5: словосочетания\n"
            "6: новые слова\n"
        )
        await query.message.reply_text(f"{categories_info} Введите слово в формате 'индекс категории - английское - русский - транскрипция':", reply_markup=get_main_menu_button())

    elif query.data == "my_words":
        words = await get_user_words(query.message.chat_id)
        if words:
            word_list = "\n".join([
                f"{w.category} - {w.english_word} - {w.russian_word}" + (f" - {w.transcription}" if w.transcription else "")
                for w in words
            ])
            total_words = len(words)

            # Разбиваем на части, если длина сообщения превышает MAX_MESSAGE_LENGTH
            for part in split_message(f"Ваш словарь:\n{word_list}\n\n📊 Всего слов в словаре: {total_words}"):
                await query.message.reply_text(part, reply_markup=get_main_menu())

        else:
            await query.message.reply_text("Ваш словарь пока пуст.")

    elif query.data == "delete_word":
        user_states[query.message.chat_id] = {"state": "deleting"}
        await query.message.reply_text("Введите слово для удаления (на английском или русском):")


    elif query.data == "finish_learning":

        if not user_states.get(query.message.chat_id):
            await query.message.reply_text(
                "Сессия обучения не найдена, попробуйте начать сначала.",
                reply_markup=get_main_menu_button()
            )
            return
        await finish_learning(update, context)

    elif query.data == "edit_category":
        user_states[query.message.chat_id] = {"state": "editing"}
        await query.message.reply_text(
            "Введите слово, для которого хотите изменить категорию (на английском или русском):"
        )



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



    # Изменение категории
    if telegram_id in user_states and user_states[telegram_id].get("state") == "editing":
        user_states[telegram_id]["word_text"] = text
        user_states[telegram_id]["state"] = "editing_category_choice"
        category_text = (
            "Введите новый номер категории:\n"
            "1: существительные\n"
            "2: глаголы\n"
            "3: прилагательные\n"
            "4: частицы\n"
            "5: словосочетания\n"
            "6: новые слова\n"
        )
        await update.message.reply_text(category_text)
        return

    # Получение новой категории
    if telegram_id in user_states and user_states[telegram_id].get("state") == "editing_category_choice":
        word_text = user_states[telegram_id].get("word_text")
        new_category_index = text.strip()
        category_map = {
            "1": "существительные",
            "2": "глаголы",
            "3": "прилагательные",
            "4": "частицы",
            "5": "словосочетания",
            "6": "новые слова",
        }

        if new_category_index not in category_map:
            await update.message.reply_text("Неверный номер категории. Попробуйте снова.")
            return

        new_category = category_map[new_category_index]

        # Обновляем категорию
        word = await sync_to_async(Word.objects.filter)(
            user__telegram_id=telegram_id
        )
        word = await sync_to_async(list)(word)
        word = next((w for w in word if w.english_word.lower() == word_text.lower() or w.russian_word.lower() == word_text.lower()), None)

        if not word:
            await update.message.reply_text("Слово не найдено.")
        else:
            word.category = new_category
            await sync_to_async(word.save)()
            await update.message.reply_text(f"Категория слова '{word.english_word}' успешно изменена на '{new_category}' ✅",reply_markup=get_main_menu())

        user_states.pop(telegram_id, None)
        return

    # Если пользователь вводит текст в неизвестном формате
    await update.message.reply_text(
        "Некорректный формат. Выберите действие из меню.",
        reply_markup=get_main_menu()
    )


# Генерация меню с категориями
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


# Обработчик команды "учиться"
async def learn_handler(update, context):
    if update.callback_query:
        await update.callback_query.message.reply_text(
            "Выберите категорию для обучения:",
            reply_markup=get_category_menu()
        )
    elif update.message:
        await update.message.reply_text(
            "Выберите категорию для обучения:",
            reply_markup=get_category_menu()
        )


# Обработчик нажатия кнопок категорий
async def category_handler(update, context):
    query = update.callback_query
    await query.answer()

    # Получаем выбранную категорию
    callback_data = query.data
    if callback_data.startswith("category:"):
        category = callback_data.split(":", 1)[1]

        telegram_id = query.from_user.id
        user_words = await sync_to_async(list)(
            Word.objects.filter(user__telegram_id=telegram_id)
        )

        if category != "все":
            user_words = [word for word in user_words if word.category == category]

        if not user_words:
            await query.edit_message_text(f"В категории '{category}' пока нет слов.")
            return

        shuffle(user_words)
        user_states[telegram_id] = {
            "state": "learning",
            "words": user_words,  # Список без изменений
            "correct": 0,
            "incorrect": 0,
            "incorrect_pairs": [],
        }

        # Берем первое слово, но НЕ удаляем его из списка
        current_word = user_words[0]
        user_states[telegram_id]["current_word"] = current_word



        # Генерируем варианты ответа
        random_answers = await generate_answer_options(current_word)


        message = f"Как переводится слово '{current_word.english_word}'?"
        if current_word.transcription:
            message += f" [{current_word.transcription}]"

        keyboard = [
            [InlineKeyboardButton(answer, callback_data=f"answer:{answer}") for answer in random_answers],
            [InlineKeyboardButton("Закончить обучение", callback_data="finish_learning")],
        ]

        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
