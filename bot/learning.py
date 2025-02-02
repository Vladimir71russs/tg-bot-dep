from bot.utils import get_main_menu_button, get_main_menu, get_user
from bot.state import user_states
from dict.models import Word
from random import shuffle, sample
from asgiref.sync import sync_to_async
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

async def generate_answer_options(current_word):
    category = current_word.category
    all_words = await sync_to_async(list)(Word.objects.filter(category=category))
    translations = [w.russian_word for w in all_words if w != current_word]

    if len(translations) < 3:
        translations += ["Заглушка"] * (3 - len(translations))

    random_answers = sample(translations, min(3, len(translations)))
    random_answers.append(current_word.russian_word)
    shuffle(random_answers)

    return random_answers


async def send_message(update, text, reply_markup=None):
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.reply_text(text, reply_markup=reply_markup)


async def start_learning(update, context):
    telegram_id = update.callback_query.message.chat_id
    user, _ = await get_user(telegram_id)

    words = await sync_to_async(list)(Word.objects.filter(user_id=user.id))

    if not words:
        await send_message(update, "Ваш словарь пуст. Добавьте слова для начала обучения.", get_main_menu_button())
        return

    shuffle(words)
    user_states[telegram_id] = {
        "state": "learning",
        "words": words,
        "correct": 0,
        "incorrect": 0,
        "incorrect_pairs": []
    }

    current_word = words.pop()
    user_states[telegram_id]["current_word"] = current_word

    random_answers = await generate_answer_options(current_word)

    message = f"Как переводится слово '{current_word.english_word}'?"
    if current_word.transcription:
        message += f" [{current_word.transcription}]"

    keyboard = [
        [InlineKeyboardButton(answer, callback_data=f"answer:{answer}") for answer in random_answers],
        [InlineKeyboardButton("Закончить обучение", callback_data="finish_learning")],
    ]


    try:
        await update.callback_query.message.edit_text(
            text=message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        await send_message(update, message, InlineKeyboardMarkup(keyboard))


async def continue_learning(update, context):
    telegram_id = update.message.chat_id if update.message else update.callback_query.message.chat_id
    user_state = user_states.get(telegram_id)

    if not user_state or user_state.get("state") != "learning":
        await send_message(update, "Вы не находитесь в режиме обучения.", get_main_menu_button())
        return

    if update.callback_query and "answer:" in update.callback_query.data:
        query = update.callback_query
        selected_answer = query.data.split("answer:")[1]

        current_word = user_state["current_word"]
        if selected_answer == current_word.russian_word:
            user_state["correct"] += 1
            await send_message(update, "Верно! 🎉")
        else:
            user_state["incorrect"] += 1
            user_state["incorrect_pairs"].append((current_word.english_word, current_word.russian_word))
            await send_message(update, f"Неправильно! '{current_word.english_word}' переводится как '{current_word.russian_word}'.")

    if not user_state["words"]:
        await finish_learning(update, context)
        return

    current_word = user_state["words"].pop()
    user_state["current_word"] = current_word

    random_answers = await generate_answer_options(current_word)

    message = f"Как переводится слово '{current_word.english_word}'?"
    if current_word.transcription:
        message += f" [{current_word.transcription}]"

    keyboard = [
        [InlineKeyboardButton(answer, callback_data=f"answer:{answer}") for answer in random_answers],
        [InlineKeyboardButton("Закончить обучение", callback_data="finish_learning")],
    ]

    await send_message(update, message, InlineKeyboardMarkup(keyboard))

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

