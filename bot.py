import os
import requests
from bs4 import BeautifulSoup
import telebot
import time

# --- Конфиги ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not TELEGRAM_BOT_TOKEN or not OPENROUTER_API_KEY:
    print("❌ Ошибка: Не заданы TELEGRAM_BOT_TOKEN или OPENROUTER_API_KEY в переменных окружения.")
    exit(1)

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# --- Ссылки для парсинга ---
URLS = {
    "основа": "https://soundmusic54.ru",
    "продакшн": "https://soundmusic54.ru/production",
    "фингерстайл": "https://soundmusic54.ru/fingerstyle",
    "электруха": "https://soundmusic54.ru/electricguitar",
    "магазин": "https://soundmusic54.ru/shop",
    "рейтинг": "https://soundmusic54.ru/top",
    "дорожная карта": "https://soundmusic54.ru/way",
    "стратегия": "https://soundmusic54.ru/plan",
    "faq": "https://soundmusic54.ru/faq",
}

def get_page_text(url):
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        main_content = soup.find("main") or soup.find("article") or soup.find("div", class_="content") or soup.body
        if main_content:
            return main_content.get_text(separator="\n", strip=True)
        else:
            return ""
    except Exception as e:
        print(f"Ошибка при загрузке {url}: {e}")
        return ""

print("⚙️ Загружаю страницы сайта...")
site_texts = {}
for name, url in URLS.items():
    print(f"Загружаю {name}...")
    site_texts[name] = get_page_text(url)
    time.sleep(1)  # Чтобы не нагружать сайт

print("✅ Загрузка сайта завершена.")

def search_in_site(question, site_texts):
    question_words = set(word.lower() for word in question.split() if len(word) > 3)
    best_match = ""
    max_hits = 0
    for section, text in site_texts.items():
        hits = sum(word in text.lower() for word in question_words)
        if hits > max_hits and hits > 0:
            max_hits = hits
            best_match = text
    if best_match:
        return best_match[:1500]
    else:
        return ""

def ask_gpt_with_context(question, context_text):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    messages = [
        {"role": "system", "content": "Ты — дружелюбный и честный помощник SoundMusic. Отвечай понятно и доброжелательно."}
    ]

    if context_text:
        messages.append({"role": "system", "content": f"Используй информацию из сайта SoundMusic:\n{context_text}"})

    messages.append({"role": "user", "content": question})

    payload = {
        "model": "tngtech/deepseek-r1t2-chimera:free",
        "messages": messages,
        "max_tokens": 400,
        "temperature": 0.7
    }

    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=15
        )
        if response.ok:
            data = response.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "⚠️ Пустой ответ.")
        else:
            print("❌ Ошибка OpenRouter:", response.status_code, response.text)
            return "⚠️ Ошибка сервиса. Попробуй позже."
    except Exception as e:
        print("❌ Исключение при обращении к OpenRouter:", str(e))
        return "⚠️ Что-то пошло не так. Попробуй позже."

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    question = message.text
    print(f"Получен вопрос: {question}")
    context = search_in_site(question, site_texts)
    answer = ask_gpt_with_context(question, context)
    bot.send_message(message.chat.id, answer)

if __name__ == "__main__":
    print("🚀 Бот запущен!")
    bot.polling(none_stop=True)
