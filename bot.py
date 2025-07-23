import os
import requests
from bs4 import BeautifulSoup
import telebot
import re
from flask import Flask, request

# --- Настройки ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Пример: https://your-bot.up.railway.app

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
app = Flask(__name__)

# --- Загрузка сайта ---
BASE_URL = "https://soundmusic54.ru"
PATHS = ["", "production", "fingerstyle", "electricguitar", "shop", "top", "way", "plan", "faq"]
site_contents = {}

def fetch_page(url):
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla"})
        resp.raise_for_status()
        return resp.text
    except requests.HTTPError as e:
        print(f"Ошибка при загрузке {url}: {e}")
        return None

def load_site():
    print("⚙️ Загружаю страницы сайта...")
    for path in PATHS:
        url = f"{BASE_URL}/{path}" if path else BASE_URL
        print(f"Загружаю {url}...")
        html = fetch_page(url)
        if html:
            soup = BeautifulSoup(html, "html.parser")
            text = soup.get_text(separator="\n", strip=True)
            site_contents[path or "base"] = text
        else:
            site_contents[path or "base"] = ""
    print("✅ Загрузка сайта завершена.")

# --- Работа с OpenRouter ---
def ask_deepseek(question: str) -> str:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    important_sections = ["base", "faq", "plan", "way"]
    site_summary = "\n\n".join(
        f"Раздел '{key}': {val[:800]}"
        for key, val in site_contents.items() if key in important_sections
    )
    system_prompt = (
        "Ты — тёплый и дружелюбный помощник школы SoundMusic. "
        "Отвечай по теме сайта. Если инфы нет — скажи честно и предложи зайти на сайт.\n"
        f"Вот данные с сайта:\n{site_summary}"
    )
    payload = {
        "model": "tngtech/deepseek-r1t2-chimera:free",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ],
        "max_tokens": 1000,
        "temperature": 0.7
    }
    try:
        resp = requests.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "").strip() or "⚠️ Пустой ответ."
    except Exception as e:
        print("❌ Ошибка запроса к OpenRouter:", str(e))
        return "⚠️ Ошибка сервиса. Попробуй позже."

# --- Помощник Telegram ---
def format_bold_markdown(text: str) -> str:
    text = text.replace("__", "*").replace("**", "*")
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    return text

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.send_message(message.chat.id,
        "Привет! Я помощник школы SoundMusic. "
        "Задавай вопросы про обучение и сайт soundmusic54.ru.")

@bot.message_handler(func=lambda m: True)
def handle_message(message):
    question = message.text.strip()
    if not question:
        bot.send_message(message.chat.id, "Пожалуйста, задай вопрос.")
        return
    bot.send_chat_action(message.chat.id, 'typing')
    answer = ask_deepseek(question)
    for i in range(0, len(answer), 4096):
        bot.send_message(message.chat.id, format_bold_markdown(answer[i:i+4096]), parse_mode="Markdown")

# --- Webhook обработка ---
@app.route(f"/{TELEGRAM_BOT_TOKEN}", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode("utf-8"))
    bot.process_new_updates([update])
    return "OK", 200

@app.route("/", methods=["GET"])
def index():
    return "Бот работает!", 200

# --- Запуск приложения ---
if __name__ == "__main__":
    load_site()

    # Удалим старый webhook и установим новый
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{TELEGRAM_BOT_TOKEN}")
    print(f"🚀 Webhook установлен: {WEBHOOK_URL}/{TELEGRAM_BOT_TOKEN}")

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
