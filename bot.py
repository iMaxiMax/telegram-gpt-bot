import os
import requests
from bs4 import BeautifulSoup
import telebot
import json
import re

# --- Настройки ---

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/115.0 Safari/537.36")
}

BASE_URL = "https://soundmusic54.ru"
PATHS = [
    "",              # основа
    "production",    # продакшн
    "fingerstyle",   # фингерстайл
    "electricguitar",# электруха
    "shop",          # магазин сша
    "top",           # рейтинг учеников
    "way",           # дорожная карта обучения
    "plan",          # стратегия обучения
    "faq"            # FAQ
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

    site_summary = "\n\n".join(
        f"Раздел '{key}': {val[:800]}"
        for key, val in site_contents.items()
    )

    system_prompt = (
        "Ты — тёплый и дружелюбный помощник SoundMusic, "
        "используй информацию с сайта для ответов, "
        "не придумывай лишнего, отвечай понятно и подробно.\n"
        f"Вот данные с сайта:\n{site_summary}"
    )

    payload = {
        "model": "tngtech/deepseek-r1t2-chimera:free",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ],
        "max_tokens": 300,
        "temperature": 0.7
    }

    try:
        resp = requests.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        answer = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return answer or "⚠️ Пустой ответ от сервиса."
    except Exception as e:
        print("❌ Ошибка запроса к OpenRouter:", str(e))
        return "⚠️ Ошибка сервиса. Попробуй позже."

def escape_markdown(text: str) -> str:
    # Экранируем специальные символы MarkdownV2 Telegram, чтобы жирный текст работал корректно
    # Telegram MarkdownV2 требует экранировать _ * [ ] ( ) ~ ` > # + - = | { } . !
    escape_chars = r'\_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

def format_bold_markdown(text: str) -> str:
    # Заменяем __текст__ на *текст* и потом экранируем все символы, кроме звездочек
    # Для MarkdownV2 жирный текст — **текст**
    # Но если мы не экранируем правильно — Telegram выдаст ошибку
    # Логика:
    # 1) заменим __текст__ на **текст**
    # 2) потом экранируем все спецсимволы, кроме звездочек внутри ** **
    # Для упрощения:
    # - заменим __текст__ на **текст**
    # - экранируем всё кроме звездочек (т.е. не экранируем сами **)
    
    # Сначала замена __текст__ на **текст**
    text = re.sub(r'__(.+?)__', r'**\1**', text)

    # Разобьём текст на куски между ** (жирным) и остальной текст
    parts = re.split(r'(\*\*.*?\*\*)', text)
    result = []
    for part in parts:
        if part.startswith("**") and part.endswith("**"):
            # внутри жирного не экранируем звездочки, но экранируем остальное
            inner = part[2:-2]
            inner_escaped = escape_markdown(inner)
            result.append(f"**{inner_escaped}**")
        else:
            # экранируем весь текст
            result.append(escape_markdown(part))
    return "".join(result)

def send_long_message(bot, chat_id, text, parse_mode=None):
    max_len = 4000
    for i in range(0, len(text), max_len):
        bot.send_message(chat_id, text[i:i+max_len], parse_mode=parse_mode)

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
    send_long_message(bot, message.chat.id, safe_answer, parse_mode="MarkdownV2")

if __name__ == "__main__":
    load_site()
    print("🚀 Бот запущен!")
    bot.polling(none_stop=True)
