import os
import logging
import django
from django.conf import settings
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

# Настройка Django для работы вне проекта
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "telegtam.settings")
django.setup()
from bot.handlers import start_handler, button_handler, text_handler
# from dict.models import User, Word

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Убедитесь, что вы добавляете обработчик для кнопки завершения обучения



def main():
    token = settings.YOUR_TELEGRAM_BOT_TOKEN
    if not token:
        raise ValueError("Токен Telegram бота не найден в настройках!")

    # Создаем приложение Telegram
    application = Application.builder().token(token).build()

    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CallbackQueryHandler(button_handler))  # Для кнопок
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))  # Для текста

    logger.info("Бот запущен через Webhook...")

    # Установите URL Webhook
    webhook_url = f"https://server-bot-tg.onrender.com/webhook/"
    application.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),  # Порт, на котором приложение слушает запросы
        url_path="webhook/",
        webhook_url=webhook_url,  # Telegram будет отправлять запросы сюда
    )

#fdf
if __name__ == "__main__":
    main()
