import os
import requests
from bs4 import BeautifulSoup
import telebot
import html

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
        html_data = fetch_page(url)
        if html_data:
            soup = BeautifulSoup(html_data, "html.parser")
            text = soup.get_text(separator="\n", strip=True)
            site_contents[path or "base"] = text
        else:
            site_contents[path or "base"] = ""
    print("✅ Загрузка сайта завершена.")

# --- Запрос к OpenRouter DeepSeek ---

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

    payload = {
        "model": "tngtech/deepseek-r1t2-chimera:free",
        "messages": [
            {
                "role": "system",
                "content": (
                    "Ты — тёплый и дружелюбный помощник SoundMusic. "
                    "Используй информацию с сайта soundmusic54.ru, "
                    "не придумывай лишнего и говори по делу, понятно и доброжелательно.\n\n"
                    f"Вот выдержки с сайта:\n{site_summary}"
                )
            },
            {
                "role": "user",
                "content": question
            }
        ],
        "max_tokens": 800,
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

# --- Telegram Обработка ---

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "Привет! Я помощник SoundMusic. "
        "Задавай вопросы про курсы, обучение и всё, что связано с сайтом https://soundmusic54.ru"
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

    # Экранируем HTML, затем возвращаем разрешённые теги
    safe_answer = html.escape(answer)
    safe_answer = safe_answer.replace("&lt;b&gt;", "<b>").replace("&lt;/b&gt;", "</b>")
    safe_answer = safe_answer.replace("&lt;i&gt;", "<i>").replace("&lt;/i&gt;", "</i>")
    safe_answer = safe_answer.replace("&lt;u&gt;", "<u>").replace("&lt;/u&gt;", "</u>")
    safe_answer = safe_answer.replace("&lt;a href=", "<a href=").replace("&gt;", ">")

    # Разбиваем на части, если длинный
    max_len = 4096
    for i in range(0, len(safe_answer), max_len):
        bot.send_message(message.chat.id, safe_answer[i:i+max_len], parse_mode="HTML")

# --- Запуск ---

if __name__ == "__main__":
    load_site()
    print("🚀 Бот запущен!")
    bot.polling(none_stop=True)
