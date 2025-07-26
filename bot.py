import os
import threading
import time
import requests
from bs4 import BeautifulSoup
import telebot
import re
from flask import Flask, request
from telebot.apihelper import ApiTelegramException
from telebot import formatting

# ================== Инициализация ================== #
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN не установен!")
    
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# ================== Markdown Helpers ================== #
def escape_markdown_v2(text: str) -> str:
    """Экранирует спецсимволы MarkdownV2"""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{"".join(re.escape(c) for c in escape_chars)}])', r'\\\1', text)

def safe_markdown(text: str) -> str:
    """Обрабатывает разметку, сохраняя корректные Markdown-конструкции"""
    patterns = {
        'bold': r'\*\*(.+?)\*\*',
        'italic': r'\*(.+?)\*',
        'code': r'`(.+?)`'
    }
    
    replacements = {}
    for key, pattern in patterns.items():
        for i, match in enumerate(re.finditer(pattern, text)):
            placeholder = f'__{key}_{i}__'
            replacements[placeholder] = match.group(0)
            text = text.replace(match.group(0), placeholder)
    
    text = escape_markdown_v2(text)
    
    for placeholder, original in replacements.items():
        text = text.replace(placeholder, original)
    
    return text

# ================== Message Splitting ================== #
def split_message(text: str, limit=4096) -> list:
    """Умное разбиение сообщения с сохранением разметки"""
    if len(text) <= limit:
        return [text]
    
    # Алгоритм разбиения с учетом Markdown (как в предыдущем ответе)
    # ... [ваша реализация из предыдущего ответа] ...
    
    return parts  # Возвращаем список частей

# ================== DeepSeek Integration ================== #
def ask_deepseek(question: str) -> str:
    """Запрос к DeepSeek API"""
    # ... [ваша реализация] ...
    return response_text

# ================== Telegram Handlers ================== #
@bot.message_handler(func=lambda m: True)
def handle_msg(m):
    """Обработчик всех текстовых сообщений"""
    # ... [реализация из предыдущего ответа с обработкой ошибок] ...

# ================== Web Server ================== #
@app.route('/')
def home():
    return "🤖 Бот активен! /health для проверки"

@app.route('/health')
def health_check():
    return "OK", 200

# ================== Startup ================== #
def run_bot():
    print("🚀 Запуск Telegram бота...")
    bot.infinity_polling()

def run_flask():
    print("🌐 Запуск веб-сервера...")
    app.run(host='0.0.0.0', port=8080)

if __name__ == '__main__':
    # Параллельный запуск бота и веб-сервера
    threading.Thread(target=run_bot, daemon=True).start()
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Вечный цикл для поддержания работы
    while True:
        time.sleep(3600)
