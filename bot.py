import os
import requests
from bs4 import BeautifulSoup
import telebot
import json

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

# --- Загрузка и подготовка сайта ---

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
            # Для простоты сохраняем чистый текст страницы
            text = soup.get_text(separator="\n", strip=True)
            site_contents[path or "base"] = text
        else:
            site_contents[path or "base"] = ""
    print("✅ Загрузка сайта завершена.")

# --- Функция запроса к OpenRouter DeepSeek ---

def ask_deepseek(question: str) -> str:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    # Добавляем в system prompt краткую сводку с сайта, чтобы бот отвечал с учетом сайта
    site_summary = "\n\n".join(
        f"Раздел '{key}': {val[:800]}"  # берем первые 800 символов для ограничения
        for key, val in site_contents.items()
    )

    payload = {
        "model": "tngtech/deepseek-r1t2-chimera:free",
        "messages": [
            {
                "role": "system",
                "content": (
                    "Ты — тёплый и дружелюбный помощник SoundMusic, "
                    "используй информацию с сайта для ответов, "
                    "не придумывай лишнего, отвечай понятно и подробно.\n"
                    f"Вот данные с сайта:\n{site_summary}"
                )
            },
            {
                "role": "user",
                "content": question
            }
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

# --- Обработка сообщений Telegram ---

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
    # Разбиваем ответ на части по 4096 символов (лимит Telegram)
    max_len = 4096
    for i in range(0, len(answer), max_len):
        bot.send_message(message.chat.id, answer[i:i+max_len])

# --- Запуск ---

if __name__ == "__main__":
    load_site()
    print("🚀 Бот запущен!")
    bot.polling(none_stop=True)
