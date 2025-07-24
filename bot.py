import os
import threading
import requests
from bs4 import BeautifulSoup
import telebot
import re
from flask import Flask

# --- Настройки ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not TELEGRAM_BOT_TOKEN or not OPENROUTER_API_KEY:
    raise RuntimeError("❌ Установите в Railway переменные TELEGRAM_BOT_TOKEN и OPENROUTER_API_KEY")

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
app = Flask(__name__)

# --- Сайт SoundMusic ---
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/115.0 Safari/537.36")
}
BASE_URL = "https://soundmusic54.ru"
PATHS = ["", "production","fingerstyle","electricguitar","shop","top","way","plan","faq"]
site_contents = {}

def fetch_page(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=5)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"❌ Ошибка при загрузке {url}: {e}")
        return ""

def load_site():
    print("⚙️ Загружаю сайт...")
    for p in PATHS:
        url = BASE_URL + ("/" + p if p else "")
        print(f" → {url}")
        html = fetch_page(url)
        text = BeautifulSoup(html, "html.parser").get_text("\n", strip=True)
        site_contents[p or "base"] = text
    print("✅ Сайт загружен.")

# --- OpenRouter/DeepSeek запрос ---
def ask_deepseek(question: str) -> str:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    summary = "\n\n".join(f"Раздел '{k}': {v[:800]}" for k,v in site_contents.items())
    system = (
        "Ты — дружелюбный помощник SoundMusic. "
        "Отвечай по информации с сайта, не выдумывай.\n"
        f"{summary}"
    )
    payload = {
        "model": "tngtech/deepseek-r1t2-chimera:free",
        "messages": [
            {"role":"system","content": system},
            {"role":"user","content": question}
        ],
        "max_tokens": 400,
        "temperature": 0.7
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "").strip() or "⚠️ Пустой ответ."
    except Exception as e:
        print(f"❌ OpenRouter error: {e}")
        return "⚠️ Сервис недоступен, попробуйте позже."

def format_md(text: str) -> str:
    # Делаем **жирным** через Markdown
    txt = re.sub(r"__(.+?)__", r"*\1*", text)
    return re.sub(r"<br\s*/?>", "\n", txt)

# --- Обработчики Telegram ---
@bot.message_handler(commands=["start","help"])
def cmd_start(m):
    bot.send_message(m.chat.id,
        "Привет! Я — помощник SoundMusic. Задавайте вопросы про обучение на soundmusic54.ru"
    )

@bot.message_handler(func=lambda m: True)
def handle_msg(m):
    q = m.text.strip()
    if not q:
        return bot.send_message(m.chat.id, "❓ Напиши вопрос текстом.")
    bot.send_chat_action(m.chat.id, "typing")
    ans = ask_deepseek(q)
    for chunk in [ans[i:i+4000] for i in range(0, len(ans), 4000)]:
        bot.send_message(m.chat.id, format_md(chunk), parse_mode="Markdown")

# --- Flask healthcheck ---
@app.route("/health")
def health():
    return "OK", 200

def run_bot():
    bot.infinity_polling(skip_pending=True)

if __name__ == "__main__":
    load_site()
    # Telegram polling в фоне
    threading.Thread(target=run_bot, daemon=True).start()
    # Запуск Flask (Railway прослушивает PORT)
    port = int(os.getenv("PORT", 5000))
    print(f"🚀 Запуск Flask на 0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port)
