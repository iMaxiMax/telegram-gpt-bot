import os
import telebot
from telebot import types
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not TOKEN or not OPENROUTER_API_KEY:
    raise ValueError("❌ TELEGRAM_TOKEN или OPENROUTER_API_KEY не заданы!")

bot = telebot.TeleBot(TOKEN)

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🎓 О школе", "💰 Цены")
    markup.row("📝 Как записаться", "🥇 Уровни учеников")
    markup.row("🎯 Цели и результат")
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(
        message.chat.id,
        "Привет! 👋 Я — навигатор экспресс-школы гитары SOUNDMUSIC.\n\nВыбери пункт:",
        reply_markup=main_menu()
    )

def ask_gpt(question: str) -> str:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "openchat/openchat-3.5:free",
        "messages": [
            {"role": "system",
             "content": "Ты — тёплый, честный помощник SoundMusic. Отвечай понятно и доброжелательно."},
            {"role": "user", "content": question}
        ],
        "max_tokens": 100,
        "temperature": 0.7
    }
    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=payload
    )
    if resp.ok:
        return resp.json()["choices"][0]["message"]["content"]
    else:
        print("Ошибка OpenRouter:", resp.status_code, resp.text)
        return "⚠️ Ошибка сервиса. Попробуй позже."

@bot.message_handler(func=lambda m: True)
def handle_message(message):
    text = message.text.strip()
    if text in ["🎓 О школе", "💰 Цены", "📝 Как записаться", "🥇 Уровни учеников", "🎯 Цели и результат"]:
        responses = {
            "🎓 О школе": "🎓 Экспресс-школа SoundMusic — https://soundmusic54.ru/#menu",
            "💰 Цены": "💰 Цены: https://soundmusic54.ru/#price",
            "📝 Как записаться": "📝 Заявка: https://soundmusic54.ru/#sign или просто ответь тут",
            "🥇 Уровни учеников": "🥇 Мы подстраиваемся под твой уровень — https://soundmusic54.ru/top",
            "🎯 Цели и результат": "🎯 Достижение цели: https://soundmusic54.ru/production"
        }
        bot.send_message(message.chat.id, responses[text])
    else:
        bot.send_chat_action(message.chat.id, 'typing')
        bot.send_message(message.chat.id, ask_gpt(text), reply_markup=main_menu())

print("🚀 Бот с openchat-3.5 запущен!")
bot.infinity_polling()
