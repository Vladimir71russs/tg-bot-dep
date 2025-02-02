import os
import django
from django.conf import settings
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

# dep
# Настройка Django для работы вне проекта
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "telegtam.settings")
django.setup()

from bot.handlers import start_handler, button_handler, text_handler, learn_handler, category_handler


def main():
    token = settings.YOUR_TELEGRAM_BOT_TOKEN
    if not token:
        raise ValueError("Токен Telegram бота не найден в настройках!")

    application = Application.builder().token(token).build()

    # Регистрация обработчиков
    application.add_handler(CallbackQueryHandler(category_handler, pattern="^category:"))  # Для обработки кнопок категорий
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CallbackQueryHandler(button_handler))  # Для кнопок
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))  # Для текста
    application.add_handler(CommandHandler("learn", learn_handler))  # Для команды /learn

    # Webhook
    webhook_url = "https://server-bot-tg.onrender.com/webhook/"
    application.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),  # Порт, на котором приложение слушает запросы
        url_path="webhook/",  # Локальный путь для Webhook
        webhook_url=webhook_url,  # Telegram будет отправлять запросы сюда
    )


if __name__ == "__main__":
    main()
