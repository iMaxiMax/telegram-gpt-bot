import os
import requests
from bs4 import BeautifulSoup
import telebot
import re
import time

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
    "", "production", "fingerstyle", "electricguitar",
    "shop", "top", "way", "plan", "faq"
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

def ask_deepseek(question: str, use_site_context=True) -> str:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    if use_site_context:
        site_summary = "\n\n".join(
            f"Раздел '{key}': {val[:800]}"
            for key, val in site_contents.items()
        )
        system_prompt = (
            "Ты — тёплый и дружелюбный помощник SoundMusic. "
            "Отвечай кратко, по делу, только по информации с сайта soundmusic54.ru. "
            "Не придумывай, если чего-то нет на сайте.\n"
            f"Вот данные с сайта:\n{site_summary}"
        )
    else:
        # Свободный, раскрепощённый помощник в группе, можно отвечать на любые вопросы
        system_prompt = (
            "Ты — дружелюбный и раскрепощённый помощник SoundMusic, "
            "отвечай на вопросы свободно и интересно."
        )

    payload = {
        "model": "tngtech/deepseek-r1t2-chimera:free",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ],
        "max_tokens": 600,
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

def format_bold_markdown(text: str) -> str:
    text = text.replace("__", "**")
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    return text

def send_long_message(chat_id, text, reply_to_message_id=None):
    max_len = 4096
    parts = []

    lines = text.split('\n')
    current_part = ""
    for line in lines:
        # Если добавление строки превышает лимит, отправляем накопленное
        if len(current_part) + len(line) + 1 > max_len:
            parts.append(current_part)
            current_part = line + '\n'
        else:
            current_part += line + '\n'
    if current_part:
        parts.append(current_part)

    for part in parts:
        if reply_to_message_id:
            bot.send_message(chat_id, part, parse_mode="Markdown", reply_to_message_id=reply_to_message_id)
        else:
            bot.send_message(chat_id, part, parse_mode="Markdown")
        time.sleep(0.4)  # Пауза, чтобы избежать ограничения Телеграма

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "Привет! Я помощник SoundMusic. "
        "Задавай вопросы про курсы, обучение и всё, что связано с сайтом soundmusic54.ru."
    )
    bot.send_message(message.chat.id, welcome_text)

@bot.message_handler(func=lambda m: m.chat.type == 'private')
def handle_private_message(message):
    question = message.text.strip()
    if not question:
        bot.send_message(message.chat.id, "Пожалуйста, задай вопрос.")
        return
    bot.send_chat_action(message.chat.id, 'typing')
    answer = ask_deepseek(question, use_site_context=True)
    safe_answer = format_bold_markdown(answer)
    send_long_message(message.chat.id, safe_answer)

@bot.message_handler(func=lambda message: message.chat.type in ['group', 'supergroup'])
def handle_group_message(message):
    bot_username = bot.get_me().username
    if f"@{bot_username}" in message.text:
        question = message.text.replace(f"@{bot_username}", "").strip()
        if question:
            bot.send_chat_action(message.chat.id, 'typing')
            answer = ask_deepseek(question, use_site_context=False)
            safe_answer = format_bold_markdown(answer)
            send_long_message(message.chat.id, safe_answer, reply_to_message_id=message.message_id)

if __name__ == "__main__":
    load_site()
    print("🚀 Бот запущен!")
    bot.polling(none_stop=True)
