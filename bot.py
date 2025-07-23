import os
import telebot
from telebot import types
import requests

# Получаем токены из переменных окружения
TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not TOKEN or not OPENROUTER_API_KEY:
    raise ValueError("❌ Переменные окружения не заданы! Проверь TELEGRAM_TOKEN и OPENROUTER_API_KEY.")

bot = telebot.TeleBot(TOKEN)

# Главное меню
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🎓 О школе", "💰 Цены")
    markup.row("📝 Как записаться", "🥇 Уровни учеников")
    markup.row("🎯 Цели и результат")
    return markup

# Обработка команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(
        message.chat.id,
        "Привет! 👋 Я — навигатор экспресс-школы гитары SOUNDMUSIC.\n\nВыбери интересующий пункт:",
        reply_markup=main_menu()
    )

# Запрос к OpenRouter (Zephyr-7B)
def ask_openrouter(prompt):
    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "huggingfaceh4/zephyr-7b-beta",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Ты — честный, тёплый и внимательный помощник школы гитары SoundMusic из Новосибирска. "
                        "Отвечай понятно, по-человечески и без давления. Если можно — с заботой и ссылкой на soundmusic54.ru."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }

        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
        result = response.json()

        return result["choices"][0]["message"]["content"]

    except Exception as e:
        print("Ошибка OpenRouter:", e)
        return "⚠️ Что-то пошло не так. Попробуй ещё раз позже."

# Обработка всех сообщений
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    text = message.text.strip()

    if text == "🎓 О школе":
        bot.send_message(message.chat.id, "🎓 Мы — экспресс-школа гитары SoundMusic. Индивидуально, по шагам, с удовольствием. Подробнее: https://soundmusic54.ru/#menu")
    elif text == "💰 Цены":
        bot.send_message(message.chat.id, "💰 Актуальные цены тут:\nhttps://soundmusic54.ru/#price")
    elif text == "📝 Как записаться":
        bot.send_message(message.chat.id, "📝 Просто оставь заявку на сайте:\nhttps://soundmusic54.ru/#sign\nИли напиши сюда, и мы поможем.")
    elif text == "🥇 Уровни учеников":
        bot.send_message(message.chat.id, "🥇 У нас учатся и новички, и профи. Подробнее: https://soundmusic54.ru/top")
    elif text == "🎯 Цели и результат":
        bot.send_message(message.chat.id, "🎯 Мы помогаем достигать цели — играть, писать музыку, выступать: https://soundmusic54.ru/production")
    else:
        bot.send_chat_action(message.chat.id, 'typing')
        reply = ask_openrouter(text)
        bot.send_message(message.chat.id, reply)

print("Бот с OpenRouter (Zephyr-7B-beta) запущен!")
bot.polling()
