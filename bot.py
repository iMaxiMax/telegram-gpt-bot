import os
import telebot
import requests
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from telebot.apihelper import ApiTelegramException
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

bot = telebot.TeleBot(BOT_TOKEN)

def main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(KeyboardButton("📚 Курсы"), KeyboardButton("🎸 Преподаватели"))
    markup.row(KeyboardButton("📍 Адрес"), KeyboardButton("📞 Контакты"))
    return markup

def ask_gpt(question: str) -> str:
    if not OPENROUTER_API_KEY:
        return "⚠️ API-ключ OpenRouter не найден."

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "tngtech/deepseek-r1t2-chimera:free",
        "messages": [
            {"role": "system", "content": "Ты — тёплый, честный помощник SoundMusic. Отвечай понятно и доброжелательно."},
            {"role": "user", "content": question}
        ],
        "max_tokens": 200,
        "temperature": 0.7
    }

    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)

        if response.ok:
            data = response.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "⚠️ Пустой ответ.")
        else:
            print("❌ Ошибка OpenRouter:", response.status_code, response.text)
            return "⚠️ Ошибка сервиса. Попробуй позже."

    except Exception as e:
        print("❌ Исключение при обращении к OpenRouter:", str(e))
        return "⚠️ Что-то пошло не так. Попробуй позже."

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, "👋 Привет! Я помощник SoundMusic. Задай вопрос или выбери опцию:", reply_markup=main_menu())

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    text = message.text.strip()
    reply = ask_gpt(text)

    try:
        if reply.strip():
            bot.send_message(message.chat.id, reply, reply_markup=main_menu())
        else:
            bot.send_message(message.chat.id, "⚠️ Ответ пустой.", reply_markup=main_menu())
    except ApiTelegramException as e:
        if "bot was blocked by the user" in str(e):
            print(f"🚫 Пользователь {message.chat.id} заблокировал бота.")
        else:
            raise e

if __name__ == '__main__':
    print("🚀 Бот с DeepSeek запущен!")
    bot.polling(none_stop=True)
