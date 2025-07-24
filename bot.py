import os
import threading
import time
import re
import requests
from bs4 import BeautifulSoup
import telebot

# ——— Настройки ———
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not TELEGRAM_BOT_TOKEN or not OPENROUTER_API_KEY:
    raise ValueError("Не заданы TELEGRAM_BOT_TOKEN или OPENROUTER_API_KEY в окружении")

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
bot.remove_webhook()  # сбрасываем вебхуки, чтобы не было конфликта polling

# Список страниц и их якорей для ссылок
PAGES = {
    "base":       "https://soundmusic54.ru",
    "production": "https://soundmusic54.ru/production",
    "fingerstyle":"https://soundmusic54.ru/fingerstyle",
    "electric":   "https://soundmusic54.ru/electricguitar",
    "shop":       "https://soundmusic54.ru/shop",
    "top":        "https://soundmusic54.ru/top",
    "way":        "https://soundmusic54.ru/way",
    "plan":       "https://soundmusic54.ru/plan",
    "faq":        "https://soundmusic54.ru/faq",
}

ANCHORS = {
    "price":    ("Цены",       "https://soundmusic54.ru/#price"),
    "feedback": ("Отзывы",     "https://soundmusic54.ru/#feedback"),
    "sign":     ("Записаться", "https://soundmusic54.ru/#sign"),
    "menu":     ("О школе",    "https://soundmusic54.ru/#menu"),
    "video":    ("Видео",      "https://soundmusic54.ru/#video"),
    "links":    ("Контакты",   "https://soundmusic54.ru/#links"),
}

# Как ключевые слова мапятся на якорь
KEYWORD_TO_ANCHOR = {
    "цена":    "price",
    "стоимость":"price",
    "отзывы":  "feedback",
    "видео":   "video",
    "запис":   "sign",
    "пробн":   "sign",
    "школ":    "menu",
    "контакт": "links",
}

# Регэкспы
MD_CLEAN_RE = re.compile(r'<br\s*/?>', re.IGNORECASE)
CYRILLIC_LINE = re.compile(r'[\u0400-\u04FF]')  # строки, содержащие хотя бы 1 кириллицу

site_contents = {}  # сюда будем класть очищенный текст каждого раздела


def fetch_and_clean(url: str) -> str:
    """Загружает страницу, парсит текст и оставляет только кириллические строки."""
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        lines = soup.get_text(separator="\n").splitlines()
        clean = [ln.strip() for ln in lines if CYRILLIC_LINE.search(ln)]
        return "\n".join(clean)
    except Exception:
        return ""


def load_site():
    """Обновляет site_contents для всех PAGES."""
    for key, url in PAGES.items():
        txt = fetch_and_clean(url)
        # храним только первые 2000 символов, чтобы не перегружать prompt
        site_contents[key] = txt[:2000]


def background_refresher():
    """Поток, который обновляет сайт раз в час."""
    while True:
        print("⚙️ Фоновая синхронизация сайта...")
        load_site()
        time.sleep(3600)


def fetch_site_summary() -> str:
    """Собирает сводку из ключевых разделов."""
    parts = []
    for key in ("base", "faq", "plan", "way"):
        text = site_contents.get(key, "")
        if text:
            parts.append(f"Раздел {key}:\n{text}")
    return "\n\n".join(parts)


def ask_model(question: str, summary: str) -> str:
    """Отправляет запрос с fallback‑логикой."""
    sys_prompt = (
        "Ты — тёплый, дружелюбный и понятный помощник школы SoundMusic. "
        "Используй только информацию из этого контекста. "
        "Если точного ответа нет — честно скажи об этом.\n\n"
        f"{summary}"
    )
    payload = {
        "messages": [
            {"role": "system", "content": sys_prompt},
            {"role": "user",   "content": question}
        ],
        "max_tokens": 700,
        "temperature": 0.3,
    }
    models = [
        "tngtech/deepseek-r1t2-chimera:free",
        "mistralai/mistral-7b-instruct:free"
    ]
    for m in models:
        try:
            payload["model"] = m
            r = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=15
            )
            if r.status_code == 200:
                data = r.json()
                msg = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                if msg:
                    return msg.strip()
        except Exception:
            pass
    return "⚠️ Извините, сейчас все модели заняты — попробуйте позже."


def clean_markdown(text: str) -> str:
    text = MD_CLEAN_RE.sub("\n", text)
    return text.replace("__", "*").replace("**", "*").strip()


def find_anchor(question: str) -> str:
    q = question.lower()
    for kw, anchor in KEYWORD_TO_ANCHOR.items():
        if kw in q:
            return anchor
    return ""


# ——— Telegram handlers —————————————————


@bot.message_handler(commands=['start', 'help'])
def send_welcome(msg):
    kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🎓 О школе", "📝 Записаться", "💰 Цены")
    bot.send_message(
        msg.chat.id,
        "Привет! Я помощник SoundMusic — задай свой вопрос.",
        reply_markup=kb
    )


@bot.message_handler(func=lambda m: True)
def handle_message(message):
    q = message.text.strip()
    if not q:
        return bot.send_message(message.chat.id, "Пожалуйста, задай вопрос.")

    bot.send_chat_action(message.chat.id, 'typing')
    summary = fetch_site_summary()
    ans = ask_model(q, summary)
    ans = clean_markdown(ans)

    # Добавляем якорную ссылку, если нужно
    akey = find_anchor(q)
    if akey in ANCHORS:
        title, url = ANCHORS[akey]
        ans += f"\n\n*Подробнее:* [{title}]({url})"

    # Разбиваем по 4096
    for i in range(0, len(ans), 4096):
        bot.send_message(
            message.chat.id,
            ans[i:i+4096],
            parse_mode="Markdown"
        )


if __name__ == "__main__":
    # Сначала синхронизируем сайт
    load_site()
    # Запускаем фоновой поток
    threading.Thread(target=background_refresher, daemon=True).start()
    print("🚀 Бот запущен и работает единственным экземпляром.")
    # Бесконечный polling с очисткой старых апдейтов
    bot.infinity_polling(skip_pending=True)
