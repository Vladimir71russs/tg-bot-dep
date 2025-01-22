from bot.state import user_states
from bot.utils import get_main_menu
from dict.models import Word, User


import re
from asgiref.sync import sync_to_async

async def add_word_to_db(telegram_id, text, update):
    # Проверяем наличие хотя бы одного разделителя "-"
    if "-" not in text:
        await update.message.reply_text(
            "Проверьте правильность ввода. Используйте формат '1-английское - русский' или '1-английское - русский - транскрипция'.",
            reply_markup=get_main_menu()
        )
        return  # Остаёмся в режиме добавления

    # Разделяем текст на части
    parts = list(map(str.strip, text.split("-", 3)))
    if len(parts) < 3:
        await update.message.reply_text(
            "Проверьте правильность ввода. Формат должен быть '1-английское - русский' или '1-английское - русский - транскрипция'.",
            reply_markup=get_main_menu()
        )
        return  # Остаёмся в режиме добавления

    # Извлекаем категорию
    category_code = parts[0]
    if not category_code.isdigit() or int(category_code) not in range(1, 7):
        await update.message.reply_text(
            "Ошибка: код категории должен быть числом от 1 до 6.",
            reply_markup=get_main_menu()
        )
        return

    # Сопоставление кодов категорий с названиями
    category_mapping = {
        "1": "существительные",
        "2": "глаголы",
        "3": "прилагательные",
        "4": "частицы",
        "5": "словосочетания",
        "6": "новые слова"
    }
    category_name = category_mapping[category_code]

    # Извлекаем слова из частей
    english_phrase = parts[1]
    russian_phrase = parts[2]
    transcription = parts[3] if len(parts) > 3 else ""  # Если транскрипция не указана, используем пустую строку

    # Проверяем, что первая часть состоит из английских слов
    if not re.fullmatch(r"[A-Za-z\s]+", english_phrase):
        await update.message.reply_text(
            "Проверьте правильность ввода. Первая часть должна содержать только английские слова или словосочетания.",
            reply_markup=get_main_menu()
        )
        return  # Остаёмся в режиме добавления

    # Проверяем, что вторая часть состоит из русских слов
    if not re.fullmatch(r"[А-Яа-яЁё\s]+", russian_phrase):
        await update.message.reply_text(
            "Проверьте правильность ввода. Вторая часть должна содержать только русские слова или словосочетания.",
            reply_markup=get_main_menu()
        )
        return  # Остаёмся в режиме добавления

    # Проверяем транскрипцию, если она указана
    if transcription and not re.fullmatch(r"[A-Za-zА-Яа-яЁё\s'ˈˌ]+", transcription):
        await update.message.reply_text(
            "Проверьте правильность ввода. Транскрипция должна быть на русском или английском, "
            "содержащей только буквы, пробелы и символы ударения (ˈ, ˌ).",
            reply_markup=get_main_menu()
        )
        return  # Остаёмся в режиме добавления

    # Если все части корректны, добавляем в базу данных
    user = await sync_to_async(User.objects.get)(telegram_id=telegram_id)
    await sync_to_async(Word.objects.create)(
        user=user,
        english_word=english_phrase,
        russian_word=russian_phrase,
        transcription=transcription,
        category=category_name
    )
    await update.message.reply_text(
        f"Слово '{english_phrase} - {russian_phrase}{f' - {transcription}' if transcription else ''}' добавлено в категорию '{category_name}'!",
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