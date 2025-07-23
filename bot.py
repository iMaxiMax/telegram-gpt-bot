import os
import requests
from bs4 import BeautifulSoup
import telebot
import json
import re
import time

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/115.0 Safari/537.36"
}

BASE_URL = "https://soundmusic54.ru"
PATHS = ["", "production", "fingerstyle", "electricguitar", "shop", "top", "way", "plan", "faq"]

site_contents = {}

def fetch_page(url):
    try:
        resp = requests.get(url, headers=HEADERS)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
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

def ask_openrouter(question: str) -> str:
    models = [
        "togethercomputer/stripedhyena-hessian:free",
        "togethercomputer/llama-3-70b-chat:free",
        "mistralai/mistral-7b-instruct:free",
        "tngtech/deepseek-r1t2-chimera:free"
    ]

    important_sections = ["base", "faq", "plan", "way"]
    site_summary = "\n\n".join(
        f"Раздел '{key}': {val[:800]}" for key, val in site_contents.items() if key in important_sections
    )

    system_prompt = (
        "Ты — тёплый и дружелюбный помощник школы SoundMusic. "
        "Если вопрос про обучение, гитару или школу — используй сайт. "
        "Если сайт не даёт ответа, говори честно и не выдумывай."
        f"\nВот данные с сайта:\n{site_summary}"
    )

    for model in models:
        print(f"🔄 Пробую модель: {model}")
        try:
            url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question}
                ],
                "max_tokens": 1000,
                "temperature": 0.7
            }

            resp = requests.post(url, headers=headers, json=payload, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            answer = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            if answer:
                return answer
        except Exception as e:
            print(f"❌ Ошибка модели {model}: {e}")
            time.sleep(1)
            continue

    return "⚠️ Все сервисы временно недоступны. Попробуй позже."

def format_bold_markdown(text: str) -> str:
    text = text.replace("__", "*").replace("**", "*")
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    return text

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "Привет! Я помощник школы гитары SoundMusic 🎸\n"
        "Задавай вопросы про курсы, обучение или гитару — я постараюсь помочь!"
    )
    bot.send_message(message.chat.id, welcome_text)

@bot.message_handler(func=lambda m: True)
def handle_message(message):
    question = message.text.strip()
    if not question:
        bot.send_message(message.chat.id, "Пожалуйста, задай вопрос.")
        return
    bot.send_chat_action(message.chat.id, 'typing')
    answer = ask_openrouter(question)
    safe_answer = format_bold_markdown(answer)
    max_len = 4096
    for i in range(0, len(safe_answer), max_len):
        bot.send_message(message.chat.id, safe_answer[i:i+max_len], parse_mode="Markdown")

if __name__ == "__main__":
    load_site()
    print("🚀 Бот запущен!")
    bot.polling(none_stop=True)
