import os
import telebot
import requests
from telebot import types

# Получаем токены из переменных окружения
TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not TOKEN or not OPENROUTER_API_KEY:
    raise ValueError("❌ Проверь TELEGRAM_TOKEN и OPENROUTER_API_KEY в переменных окружения")

bot = telebot.TeleBot(TOKEN)

# Главное меню
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🎓 О школе", "💰 Цены")
    markup.row("📝 Как записаться", "🥇 Уровни учеников")
    markup.row("🎯 Цели и результат")
    return markup

# Обращение к OpenRouter
def ask_openrouter(prompt):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://yourdomain.com",  # Укажи свой домен или telegram-username
        "X-Title": "SoundMusicBot"
    }

    data = {
        "model": "mistralai/mistral-7b-instruct:free",
        "messages": [
            {"role": "system", "content": "Ты — тёплый и внимательный помощник школы гитары SoundMusic из Новосибирска."},
            {"role": "user", "content": prompt}
        ]
    }

    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)

    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        print("Ошибка OpenRouter:", response.text)
        return "⚠️ Что-то пошло не так. Попробуй ещё раз позже."

# Ответ на /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(
        message.chat.id,
        "Привет! 👋 Я — навигатор экспресс-школы гитары SOUNDMUSIC.\n\nВыбери интересующий пункт:",
        reply_markup=main_menu()
    )

# Обработка всех сообщений
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    text = message.text.strip()

    if text == "🎓 О школе":
        bot.send_message(message.chat.id, "🎓 Мы — экспресс-школа гитары soundmusic... https://soundmusic54.ru/#menu")
    elif text == "💰 Цены":
        bot.send_message(message.chat.id, "💰 Цены тут:\nhttps://soundmusic54.ru/#price")
    elif text == "📝 Как записаться":
        bot.send_message(message.chat.id, "📝 Оставь заявку на сайте:\nhttps://soundmusic54.ru/#sign")
    elif text == "🥇 Уровни учеников":
        bot.send_message(message.chat.id, "🥇 У нас учатся и новички, и профи: https://soundmusic54.ru/top")
    elif text == "🎯 Цели и результат":
        bot.send_message(message.chat.id, "🎯 Мы поможем достичь цели: https://soundmusic54.ru/production")
    else:
        bot.send_chat_action(message.chat.id, 'typing')
        try:
            reply = ask_openrouter(text)
            bot.send_message(message.chat.id, reply)
        except Exception as e:
            print("Ошибка GPT:", e)
            bot.send_message(message.chat.id, "⚠️ Ошибка. Попробуй позже.")

print("Бот с OpenRouter запущен!")
bot.polling()
