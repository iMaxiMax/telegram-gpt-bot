import os
import threading
import time
import requests
from bs4 import BeautifulSoup
import telebot
import re
from flask import Flask
from telebot.apihelper import ApiTelegramException

# --- Настройки ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not TELEGRAM_BOT_TOKEN or not OPENROUTER_API_KEY:
    raise RuntimeError("❌ TELEGRAM_BOT_TOKEN и OPENROUTER_API_KEY должны быть заданы")

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
app = Flask(__name__)

# --- Загрузка сайта ---
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/115.0 Safari/537.36")
}
BASE_URL = "https://soundmusic54.ru"
PATHS = ["", "production", "fingerstyle", "electricguitar", "shop", "top", "way", "plan", "faq"]
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

# --- OpenRouter запрос ---
def ask_deepseek(question: str) -> str:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    summary = "\n\n".join(f"Раздел '{k}': {v[:800]}" for k, v in site_contents.items())

    system = (
        "Ты — тёплый и дружелюбный помощник школы гитары SoundMusic из Новосибирска.\n"
        "Отвечай **только** по фактам с сайта soundmusic54.ru, **никаких выдуманных цифр**.\n"
        "Если тебя спрашивают цену, просто отправь ссылку на раздел Цены: https://soundmusic54.ru/#price\n"
        "Если информации на сайте нет — честно скажи об этом и предложи посетить сайт.\n\n"
        f"Данные сайта (обрезано до 800 символов на раздел):\n{summary}"
    )
    payload = {
        "model": "tngtech/deepseek-r1t2-chimera:free",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": question}
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

# ФУНКЦИЯ ИСПРАВЛЕНА: Экранирование Markdown-символов
def safe_markdown(text: str) -> str:
    """
    Экранирует все спецсимволы Markdown в тексте
    чтобы избежать ошибок парсинга в Telegram
    """
    # Список символов для экранирования
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    for char in escape_chars:
        text = text.replace(char, '\\' + char)
    return text

# ФУНКЦИЯ ИСПРАВЛЕНА: Улучшенное разбиение сообщений
def split_message(text: str, limit=4096):
    """
    Разбивает текст на части с учетом:
    - Максимальной длины сообщения в Telegram
    - Сохранения целостности абзацев
    """
    if len(text) <= limit:
        return [text]
    
    parts = []
    current_chunk = ""
    
    # Разбиваем по абзацам
    paragraphs = text.split('\n\n')
    
    for para in paragraphs:
        # Если абзац слишком длинный, разбиваем на строки
        if len(para) > limit:
            lines = para.split('\n')
            for line in lines:
                if len(current_chunk) + len(line) + 1 > limit:
                    if current_chunk:
                        parts.append(current_chunk.strip())
                        current_chunk = ""
                current_chunk += line + "\n"
        else:
            if len(current_chunk) + len(para) + 2 > limit:
                if current_chunk:
                    parts.append(current_chunk.strip())
                    current_chunk = ""
            current_chunk += para + "\n\n"
    
    if current_chunk.strip():
        parts.append(current_chunk.strip())
    
    return parts

# --- Telegram handlers ---
@bot.message_handler(commands=["start", "help"])
def cmd_start(m):
    bot.send_message(m.chat.id,
        "Привет! Я — помощник SoundMusic. Задавай вопросы про обучение на soundmusic54.ru"
    )

@bot.message_handler(func=lambda m: True)
def handle_msg(m):
    q = m.text.strip()
    if not q:
        return bot.send_message(m.chat.id, "❓ Напиши, пожалуйста, текстом.")
    bot.send_chat_action(m.chat.id, "typing")
    ans = ask_deepseek(q)
    
    # ОБРАБОТКА ИСПРАВЛЕНА: Экранирование + разбиение
    safe_text = safe_markdown(ans)  # Экранируем спецсимволы
    chunks = split_message(safe_text)  # Разбиваем на части
    
    for chunk in chunks:
        try:
            # ДОБАВЛЕНО: disable_web_page_preview для избежания конфликтов
            bot.send_message(
                m.chat.id, 
                chunk, 
                parse_mode="MarkdownV2",  # Используем более стабильную версию
                disable_web_page_preview=True
            )
        except Exception as e:
            print(f"⚠️ Ошибка отправки: {e}")
            # Фоллбэк: отправка без разметки
            bot.send_message(m.chat.id, chunk)

# --- Flask healthcheck ---
@app.route("/health")
def health():
    return "OK", 200

# --- Robust polling loop ---
def run_bot():
    while True:
        try:
            # ДОБАВЛЕНО: Очистка вебхуков перед запуском
            bot.remove_webhook()
            bot.infinity_polling(skip_pending=True)
        except ApiTelegramException as e:
            desc = e.result_json.get("description", "")
            if "Conflict" in desc:
                print("⚠️ 409 Conflict — перезапуск polling через 5 сек")
                time.sleep(5)
                continue
            else:
                print("❌ Ошибка polling:", e)
                time.sleep(5)
        except Exception as e:
            print("❌ Неожиданная ошибка polling:", e)
            time.sleep(5)

# ✅ Эти функции вызываются сразу при запуске Gunicorn
load_site()
threading.Thread(target=run_bot, daemon=True).start()
