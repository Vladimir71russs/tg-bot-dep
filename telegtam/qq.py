import os
from dotenv import load_dotenv

load_dotenv()

print(f"SECRET_KEY: {os.getenv('SECRET_KEY')}")
print(f"DATABASE_PASSWORD: {os.getenv('DATABASE_PASSWORD')}")
print(f"YOUR_TELEGRAM_BOT_TOKEN: {os.getenv('YOUR_TELEGRAM_BOT_TOKEN')}")
