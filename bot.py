import os
import telebot
from telebot import types
import requests

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not TELEGRAM_TOKEN or not OPENROUTER_API_KEY:
    raise ValueError("❌ TELEGRAM_TOKEN или OPENROUTER_API_KEY не заданы!")

bot = telebot.TeleBot(TELEGRAM_TOKEN)

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
        "Привет! 👋 Я — навигатор экспресс-школы гитары SOUNDMUSIC.\n\nВыбери интересующий пункт:",
        reply_markup=main_menu()
    )

def ask_gpt(question):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://t.me/YourBotUsername",  # Замени на ссылку на своего бота
        "Content-Type": "application/json"
    }
    data = {
        "model": "openai/gpt-4",
        "messages": [
            {"role": "system", "content": "Ты — честный, тёплый и внимательный помощник школы гитары SoundMusic из Новосибирска. Отвечай дружелюбно и понятно."},
            {"role": "user", "content": question}
        ]
    }
    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        print("Ошибка OpenRouter:", response.text)
        return "⚠️ Произошла ошибка при обращении к OpenRouter."

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    text = message.text.strip()

    if text == "🎓 О школе":
        bot.send_message(message.chat.id, "🎓 Мы — экспресс-школа гитары soundmusic, обучаем с нуля и не только. Подробнее: https://soundmusic54.ru/#menu")
    elif text == "💰 Цены":
        bot.send_message(message.chat.id, "💰 Цены: https://soundmusic54.ru/#price")
    elif text == "📝 Как записаться":
        bot.send_message(message.chat.id, "📝 Запишись на сайте:\nhttps://soundmusic54.ru/#sign\nИли пиши сюда.")
    elif text == "🥇 Уровни учеников":
        bot.send_message(message.chat.id, "🥇 Учим и новичков, и профи: https://soundmusic54.ru/top")
    elif text == "🎯 Цели и результат":
        bot.send_message(message.chat.id, "🎯 Достигаем цели вместе: https://soundmusic54.ru/production")
    else:
        try:
            bot.send_chat_action(message.chat.id, 'typing')
            reply = ask_gpt(text)
            bot.send_message(message.chat.id, reply)
        except Exception as e:
            print("Ошибка:", e)
            bot.send_message(message.chat.id, "⚠️ Что-то пошло не так. Попробуй позже.")

print("Бот запущен!")
bot.polling()
