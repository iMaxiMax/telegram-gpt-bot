import os
import requests
from bs4 import BeautifulSoup
import telebot
import json
import re
from flask import Flask, request

# --- Настройки ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Например: https://worker-production-c8215.up.railway.app

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
app = Flask(__name__)

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/115.0 Safari/537.36")
}

BASE_URL = "https://soundmusic54.ru"
PATHS = [
    "",              # основа
    "production",
    "fingerstyle",
    "electricguitar",
    "shop",
    "top",
    "way",
    "plan",
    "faq"
]

site_contents = {}

def fetch_page(url):
    try:
        resp = requests.get(url, headers=HEADERS)
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
        "Помогай пользователю, опираясь на информацию с сайта. "
        "Если точной информации нет — честно скажи об этом и предложи связаться с администратором или перейти на сайт. "
        "Не выдумывай. Отвечай понятно и по делу.\n"
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
        answer = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        return answer or "⚠️ Пустой ответ от сервиса."
    except Exception as e:
        print("❌ Ошибка запроса к OpenRouter:", str(e))
        return "⚠️ Ошибка сервиса. Попробуй позже."

def format_bold_markdown(text: str) -> str:
    # Заменяем __текст__ и **текст** на *текст* для Telegram Markdown
    text = text.replace("__", "*").replace("**", "*")
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    return text

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "Привет! Я помощник SoundMusic. "
        "Задавай вопросы про курсы, обучение и всё, что связано с сайтом soundmusic54.ru."
    )
    bot.send_message(message.chat.id, welcome_text)

@bot.message_handler(func=lambda m: True)
def handle_message(message):
    question = message.text.strip()
    if not question:
        bot.send_message(message.chat.id, "Пожалуйста, задай вопрос.")
        return
    bot.send_chat_action(message.chat.id, 'typing')
    answer = ask_deepseek(question)
    safe_answer = format_bold_markdown(answer)
    max_len = 4096
    for i in range(0, len(safe_answer), max_len):
        bot.send_message(message.chat.id, safe_answer[i:i+max_len], parse_mode="Markdown")

# Webhook endpoint для Telegram
@app.route('/' + TELEGRAM_BOT_TOKEN, methods=['POST'])
def webhook():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return '', 200

if __name__ == "__main__":
    load_site()
    print("⚙️ Загрузка сайта завершена.")

    # Установка webhook вручную при старте
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL + '/' + TELEGRAM_BOT_TOKEN)
    print(f"Webhook установлен на {WEBHOOK_URL}/{TELEGRAM_BOT_TOKEN}")

    # Запускаем Flask сервер
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
