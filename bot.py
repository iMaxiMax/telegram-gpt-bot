import os
import requests
from bs4 import BeautifulSoup
import telebot
import re

# ——— Настройки ———
TELEGRAM_BOT_TOKEN   = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY   = os.getenv("OPENROUTER_API_KEY")
CONTENT_API_URL      = os.getenv("CONTENT_API_URL", "http://api:5000/content")
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Якорные ссылки
ANCHORS = {
    "menu":     ("О школе",         "https://soundmusic54.ru/#menu"),
    "sign":     ("Бесплатная неделя", "https://soundmusic54.ru/#sign"),
    "feedback": ("Отзывы",          "https://soundmusic54.ru/#feedback"),
    "video":    ("Видео учеников",  "https://soundmusic54.ru/#video"),
    "price":    ("Цены",            "https://soundmusic54.ru/#price"),
    "links":    ("Контакты",        "https://soundmusic54.ru/#links"),
}

# Фразы-подсказки к ключевым словам
KEYWORD_TO_ANCHOR = {
    "цена":    "price",
    "стоимость":"price",
    "отзывы":  "feedback",
    "видео":   "video",
    "запис":   "sign",     # запись, записаться, заявка
    "пробн":   "sign",     # пробный, пробная
    "школ":    "menu",     # школа, о школе
    "контакт": "links",    # контакты
}

# Регулярки для Markdown-очистки
MD_CLEAN_RE = re.compile(r'<br\s*/?>', re.IGNORECASE)

# ——— Помощники —————————————————

def fetch_site_summary():
    """Запрос к API-серверу, который возвращает весь текст сайта."""
    try:
        r = requests.get(CONTENT_API_URL, timeout=5)
        r.raise_for_status()
        return r.json().get("content", "")
    except Exception:
        return ""

def ask_model(question: str, site_summary: str) -> str:
    """Отправляет запрос в OpenRouter и возвращает ответ."""
    system_prompt = (
        "Ты — тёплый, дружелюбный и понятный помощник школы SoundMusic. "
        "Используй только информацию с сайта. "
        "Если точного ответа нет — честно скажи об этом и предложи обратиться к администратору.\n\n"
        f"{site_summary[:2000]}"
    )

    payload = {
        "model": "tngtech/deepseek-r1t2-chimera:free",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": question}
        ],
        "max_tokens": 800,
        "temperature": 0.3,
    }

    for model in (
        "tngtech/deepseek-r1t2-chimera:free",
        "mistralai/mistral-7b-instruct:free"
    ):
        payload["model"] = model
        try:
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
                content = data["choices"][0]["message"]["content"].strip()
                if content:
                    return content
        except Exception:
            pass
    return "⚠️ Все модели недоступны, попробуйте позже."

def clean_markdown(text: str) -> str:
    """Простая очистка Markdown-ish HTML-тегов и подчистка подчёркиваний."""
    text = MD_CLEAN_RE.sub("\n", text)
    return text.replace("__", "*").replace("**", "*")

def find_anchor(question: str) -> str:
    """По ключевым словам в вопросе возвращает якорь или пусто."""
    q = question.lower()
    for kw, anchor in KEYWORD_TO_ANCHOR.items():
        if kw in q:
            return anchor
    return ""

# ——— Обработчики ——————————————

@bot.message_handler(commands=['start', 'help'])
def send_welcome(msg):
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("🎓 О школе", "📝 Записаться", "💰 Цены")
    msg = bot.send_message(
        msg.chat.id,
        "Привет! Я помощник SoundMusic. Спроси про занятия, цены или оставь заявку.",
        reply_markup=keyboard
    )

@bot.message_handler(func=lambda m: True)
def handle_message(message):
    question = message.text.strip()
    if not question:
        return bot.send_message(message.chat.id, "Пожалуйста, задай вопрос.")

    bot.send_chat_action(message.chat.id, 'typing')

    # Получаем актуальный текст сайта
    summary = fetch_site_summary()

    # Основной ответ от AI
    answer = ask_model(question, summary)
    answer = clean_markdown(answer)

    # Определяем, стоит ли предложить ссылку
    anchor_key = find_anchor(question)
    if anchor_key and anchor_key in ANCHORS:
        title, url = ANCHORS[anchor_key]
        answer += f"\n\n*Подробнее:* [{title}]({url})"

    # Отправляем в Telegram, разбивая на 4096 символов
    for i in range(0, len(answer), 4096):
        bot.send_message(
            message.chat.id,
            answer[i:i+4096],
            parse_mode="Markdown"
        )

# ——— Запуск —————————————————————————

if __name__ == "__main__":
    bot.infinity_polling()
