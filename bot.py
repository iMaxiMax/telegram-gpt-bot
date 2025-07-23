import os
import requests
import telebot
from bs4 import BeautifulSoup

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Стабильные бесплатные модели
MODEL_LIST = [
    "openchat/openchat-7b:free",
    "mistralai/mistral-7b-instruct:free",
    "turing/turing-mixtral-8x7b:free",
    "tngtech/deepseek-r1t2-chimera:free"
]

# Сайт, который парсим
SITE_URLS = [
    "https://soundmusic54.ru",
    "https://soundmusic54.ru/production",
    "https://soundmusic54.ru/fingerstyle",
    "https://soundmusic54.ru/electricguitar",
    "https://soundmusic54.ru/shop",
    "https://soundmusic54.ru/top",
    "https://soundmusic54.ru/way",
    "https://soundmusic54.ru/plan",
    "https://soundmusic54.ru/faq",
]

site_data = ""

def load_site():
    global site_data
    print("⚙️ Загружаю страницы сайта...")
    text_blocks = []
    for url in SITE_URLS:
        print(f"Загружаю {url}...")
        try:
            resp = requests.get(url, timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")
            text = soup.get_text(separator=' ', strip=True)
            text_blocks.append(text)
        except Exception as e:
            print(f"❌ Ошибка при загрузке {url}: {e}")
    site_data = "\n".join(text_blocks)
    print("✅ Загрузка сайта завершена.\n")

def ask_openrouter(message_text):
    for model in MODEL_LIST:
        print(f"🔄 Пробую модель: {model}")
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        json_data = {
            "model": model,
            "messages": [
                {"role": "system", "content": f"Ты умный, добрый, краткий помощник для сайта soundmusic54.ru. Используй знания с сайта."},
                {"role": "user", "content": f"{message_text}\n\nКонтент сайта:\n{site_data[:4000]}"}
            ]
        }
        try:
            r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=json_data, timeout=20)
            r.raise_for_status()
            response = r.json()
            return response["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"❌ Ошибка модели {model}: {e}")
    return "⚠️ Ошибка сервиса. Попробуй позже."

@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
    bot.send_message(message.chat.id, "👋 Привет! Задай мне вопрос по сайту https://soundmusic54.ru")

@bot.message_handler(func=lambda m: True)
def handle_message(message):
    bot.send_chat_action(message.chat.id, 'typing')
    try:
        response = ask_openrouter(message.text)
        bot.send_message(message.chat.id, response)
    except Exception as e:
        print(f"❌ Ошибка в обработке сообщения: {e}")
        bot.send_message(message.chat.id, "⚠️ Что-то пошло не так...")

# Flask-заглушка для Railway health-check
from flask import Flask
app = Flask(__name__)

@app.route('/')
@app.route('/health')
def health():
    return "ok", 200

if __name__ == "__main__":
    load_site()
    print("🚀 Бот запущен!")
    from threading import Thread
    Thread(target=lambda: bot.infinity_polling(timeout=60, long_polling_timeout=10)).start()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
