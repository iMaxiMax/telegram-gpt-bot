import os
import requests
from bs4 import BeautifulSoup
import telebot
import re

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

BASE_URL = "https://soundmusic54.ru"
PATHS = ["", "production", "fingerstyle", "electricguitar", "shop", "top", "way", "plan", "faq"]

site_contents = {}

def fetch_page(url):
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        return resp.text
    except Exception:
        return ""

def load_site():
    for path in PATHS:
        url = f"{BASE_URL}/{path}" if path else BASE_URL
        html = fetch_page(url)
        if html:
            soup = BeautifulSoup(html, "html.parser")
            text = soup.get_text(separator="\n", strip=True)
            site_contents[path or "base"] = text
        else:
            site_contents[path or "base"] = ""

def ask_model(question):
    important_sections = ["base", "faq", "plan", "way"]
    site_summary = "\n\n".join(
        f"Раздел '{key}': {val[:800]}"
        for key, val in site_contents.items() if key in important_sections
    )

    system_prompt = (
        "Ты — тёплый и дружелюбный помощник школы SoundMusic. "
        "Помогай пользователю, опираясь на информацию с сайта. "
        "Если точной информации нет — честно скажи об этом и предложи обратиться к администратору или перейти на сайт.\n\n"
        f"Вот данные с сайта:\n{site_summary}"
    )

    payload = {
        "model": "tngtech/deepseek-r1t2-chimera:free",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ],
        "max_tokens": 800,
        "temperature": 0.3
    }

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=20
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return "⚠️ Ошибка при запросе. Попробуйте позже."

def clean_markdown(text):
    text = text.replace("__", "*").replace("**", "*")
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    return text

@bot.message_handler(commands=['start', 'help'])
def welcome(message):
    bot.send_message(message.chat.id, "Привет! Я помощник школы SoundMusic. Задай вопрос о занятиях, расписании, ценах и т.д.")

@bot.message_handler(func=lambda m: True)
def handle_message(message):
    question = message.text.strip()
    if not question:
        bot.send_message(message.chat.id, "Пожалуйста, задай вопрос.")
        return

    bot.send_chat_action(message.chat.id, 'typing')
    answer = ask_model(question)
    cleaned = clean_markdown(answer)
    for i in range(0, len(cleaned), 4096):
        bot.send_message(message.chat.id, cleaned[i:i+4096], parse_mode="Markdown")

if __name__ == "__main__":
    load_site()
    bot.polling(none_stop=True)
