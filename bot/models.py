import re
from asgiref.sync import sync_to_async

from bot.state import user_states
from bot.utils import get_main_menu_button, get_main_menu
from dict.models import Word, User

async def add_word_to_db(telegram_id, text, update):
    # Проверяем наличие разделителя "-"
    if "-" not in text:
        await update.message.reply_text(
            "Проверьте правильность ввода. Используйте формат 'английское - русский - транскрипция'.",
        reply_markup=get_main_menu()
        )
        return  # Остаёмся в режиме добавления

    # Разделяем текст на три части
    try:
        english_word, russian_word, transcription = map(str.strip, text.split("-", 2))
    except ValueError:
        await update.message.reply_text(
            "Проверьте правильность ввода. Убедитесь, что текст содержит два '-' между словами.",
        reply_markup=get_main_menu()
        )
        return  # Остаёмся в режиме добавления

    # Проверяем первое слово (должно быть на английском)
    if not re.fullmatch(r"[A-Za-z\s]+", english_word):
        await update.message.reply_text(
            "Проверьте правильность ввода. Первое слово должно быть на английском.",
        reply_markup=get_main_menu()
        )
        return  # Остаёмся в режиме добавления

    # Проверяем второе слово (должно быть на русском)
    if not re.fullmatch(r"[А-Яа-яЁё\s]+", russian_word):
        await update.message.reply_text(
            "Проверьте правильность ввода. Второе слово должно быть на русском.",
        reply_markup=get_main_menu()
        )
        return  # Остаёмся в режиме добавления

    # Проверяем транскрипцию (может быть на русском или английском)
    if not re.fullmatch(r"[A-Za-zА-Яа-яЁё\s'ˈˌ]+", transcription):
        await update.message.reply_text(
            "Проверьте правильность ввода. Транскрипция должна быть на русском или английском, "
            "содержащей только буквы, пробелы и символы ударения (ˈ, ˌ).",
        reply_markup=get_main_menu()
        )
        return  # Остаёмся в режиме добавления

    # Если все три части корректны, добавляем в базу данных
    user = await sync_to_async(User.objects.get)(telegram_id=telegram_id)
    await sync_to_async(Word.objects.create)(
        user=user, english_word=english_word, russian_word=russian_word, transcription=transcription
    )
    await update.message.reply_text(
        f"Слово '{english_word} - {russian_word} - {transcription}' добавлено в словарь!",
        reply_markup=get_main_menu()
    )
    user_states.pop(telegram_id, None)  # Сбрасываем состояние, так как добавление завершено


async def delete_word_from_db(telegram_id, text, update):
    user = await sync_to_async(User.objects.get)(telegram_id=telegram_id)
    word = await sync_to_async(
        lambda: Word.objects.filter(user=user).filter(
            english_word__iexact=text
        ) | Word.objects.filter(user=user).filter(
            russian_word__iexact=text
        )
    )()

    if await sync_to_async(word.exists)():
        deleted_word = await sync_to_async(word.first)()
        deleted_text = f"{deleted_word.english_word} - {deleted_word.russian_word}"
        await sync_to_async(word.delete)()
        await update.message.reply_text(f"Слово '{deleted_text}' удалено.",
                                        reply_markup=get_main_menu())
    else:
        await update.message.reply_text(f"Слово '{text}' не найдено.",
                                        reply_markup=get_main_menu())


async def get_user_words(telegram_id):
    # Находим пользователя по telegram_id
    user = await sync_to_async(User.objects.get)(telegram_id=telegram_id)
    # Получаем список слов для пользователя
    return await sync_to_async(list)(
        Word.objects.filter(user=user).all()
    )