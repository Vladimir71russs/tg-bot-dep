from bot.utils import get_main_menu_button, get_main_menu, get_user
from bot.state import user_states
from dict.models import Word
from random import shuffle, sample
from asgiref.sync import sync_to_async
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


async def generate_answer_options(current_word, reverse=False):
    category = current_word.category
    all_words = await sync_to_async(list)(Word.objects.filter(category=category))

    if reverse:
        options = [w.english_word for w in all_words if w != current_word]
        correct_answer = current_word.english_word
    else:
        options = [w.russian_word for w in all_words if w != current_word]
        correct_answer = current_word.russian_word

    if len(options) < 3:
        options += ["Заглушка"] * (3 - len(options))

    random_answers = sample(options, min(3, len(options)))
    random_answers.append(correct_answer)
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
        await send_message(update, "Ваш словарь пуст.", get_main_menu_button())
        return

    shuffle(words)
    user_states[telegram_id] = {
        "state": "learning",
        "reverse": False,
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
        await update.callback_query.message.edit_text(text=message, reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception:
        await send_message(update, message, InlineKeyboardMarkup(keyboard))


async def continue_learning(update, context):
    telegram_id = update.message.chat_id if update.message else update.callback_query.message.chat_id
    user_state = user_states.get(telegram_id)
    if not user_state or user_state.get("state") != "learning":
        await send_message(update, "Вы не в режиме обучения.", get_main_menu_button())
        return

    reverse_mode = user_state.get("reverse", False)
    if update.callback_query and "answer:" in update.callback_query.data:
        query = update.callback_query
        selected_answer = query.data.split("answer:")[1]
        current_word = user_state["current_word"]

        if reverse_mode:
            is_correct = selected_answer == current_word.english_word
        else:
            is_correct = selected_answer == current_word.russian_word

        if is_correct:
            user_state["correct"] += 1
            await send_message(update, "Верно! 🎉")
        else:
            user_state["incorrect"] += 1
            pair = (current_word.russian_word, current_word.english_word) if reverse_mode else (
                current_word.english_word, current_word.russian_word)
            user_state["incorrect_pairs"].append(pair)
            if reverse_mode:
                await send_message(update, f"Неправильно! '{current_word.russian_word}' → '{current_word.english_word}'.")
            else:
                await send_message(update, f"Неправильно! '{current_word.english_word}' → '{current_word.russian_word}'.")

    if not user_state["words"]:
        await finish_learning(update, context)
        return

    current_word = user_state["words"].pop()
    user_state["current_word"] = current_word
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
    await send_message(update, message, InlineKeyboardMarkup(keyboard))


async def finish_learning(update, context):
    telegram_id = update.callback_query.message.chat_id if update.callback_query else update.message.chat_id
    user_state = user_states.pop(telegram_id, None)
    if not user_state or user_state.get("state") != "learning":
        await send_message(update, "Вы не находились в режиме обучения.", get_main_menu_button())
        return

    correct = user_state["correct"]
    incorrect = user_state["incorrect"]
    incorrect_pairs = user_state["incorrect_pairs"]
    result_message = f"Обучение завершено!\n\n✅ Правильных: {correct}\n❌ Ошибок: {incorrect}\n\n"
    if incorrect_pairs:
        result_message += "Ошибки:\n"
        for left, right in incorrect_pairs:
            result_message += f"- {left} → {right}\n"

    await send_message(update, result_message, get_main_menu())
