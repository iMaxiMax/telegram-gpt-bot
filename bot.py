import os
import requests
import telebot

# --- Настройки ---

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# --- Ключевые факты с сайта, которые подаем модели ---
# Обновляй этот словарь вручную при изменениях на сайте!

SITE_FACTS = """
- Бесплатное пробное занятие — 1 занятие.
- Пробная неделя обучения отсутствует.
- Стоимость обучения зависит от формата (акустика, электрогитара, фингерстайл) и длительности курса.
- Для уточнения стоимости и записи звоните: +7 923 0000 508 (WhatsApp/Telegram).
- Школа гарантирует индивидуальный подход и 100% результат при выполнении рекомендаций.
"""

# --- Функция для запроса к OpenRouter DeepSeek ---

def ask_deepseek(question: str) -> str:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    system_prompt = (
        "Ты — тёплый и дружелюбный помощник SoundMusic.\n"
        "Используй только точную информацию из этих данных:\n"
        f"{SITE_FACTS}\n"
        "Не придумывай ничего лишнего. Если точной информации нет, честно скажи, что лучше уточнить у администрации."
    )

    payload = {
        "model": "tngtech/deepseek-r1t2-chimera:free",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ],
        "max_tokens": 300,
        "temperature": 0.5,
        "top_p": 1,
        "frequency_penalty": 0,
        "presence_penalty": 0
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

# --- Функция для безопасного преобразования Markdown в Telegram MarkdownV2 ---
import re
def markdown_to_telegram_md(text: str) -> str:
    # Экранируем специальные символы Telegram MarkdownV2
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    def esc(m):
        char = m.group(0)
        if char == "*":
            # заменим **текст** на Telegram жирный __текст__
            return ""
        return "\\" + char
    # Заменяем двойные **...** на __...__ (жирный в MarkdownV2)
    text = re.sub(r"\*\*(.+?)\*\*", r"__\1__", text)
    # Экранируем остальные спецсимволы
    text = re.sub(f"[{re.escape(escape_chars)}]", esc, text)
    return text

# --- Обработка сообщений Telegram ---

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "Привет! Я помощник SoundMusic.\n"
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
    safe_answer = markdown_to_telegram_md(answer)

    # Отправляем ответ по частям, если длинный
    max_len = 4096
    for i in range(0, len(safe_answer), max_len):
        bot.send_message(message.chat.id, safe_answer[i:i+max_len], parse_mode="MarkdownV2")

# --- Запуск ---

if __name__ == "__main__":
    print("🚀 Бот запущен!")
    bot.polling(none_stop=True)
