import os
import telebot
from telebot import types
from openrouter import OpenRouter

# Получаем токены из переменных окружения
TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")

if not TOKEN or not OPENROUTER_KEY:
    raise ValueError("❌ Задайте TELEGRAM_TOKEN и OPENROUTER_API_KEY в переменных окружения!")

bot = telebot.TeleBot(TOKEN)
client = OpenRouter(api_key=OPENROUTER_KEY)

# Главное меню с кнопками
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

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    text = message.text.strip()

    # Обработка кнопок меню
    if text == "🎓 О школе":
        bot.send_message(message.chat.id, "🎓 Мы — экспресс-школа гитары soundmusic, обучаем с нуля и не только. Индивидуально, по шагам, с удовольствием. Что у нас есть для тебя? Знакомься: https://soundmusic54.ru/#menu")
    elif text == "💰 Цены":
        bot.send_message(message.chat.id, "💰 Актуальные цены на обучение можно посмотреть тут:\nhttps://soundmusic54.ru/#price")
    elif text == "📝 Как записаться":
        bot.send_message(message.chat.id, "📝 Просто оставь заявку на сайте:\nhttps://soundmusic54.ru/#sign\nИли напиши сюда, и мы поможем.")
    elif text == "🥇 Уровни учеников":
        bot.send_message(message.chat.id, "🥇 У нас учатся и новички, и профи. Программа подстраивается под твой уровень: https://soundmusic54.ru/top")
    elif text == "🎯 Цели и результат":
        bot.send_message(message.chat.id, "🎯 Мы помогаем достичь твоей цели: научиться играть, писать музыку или выступать: https://soundmusic54.ru/production")
    else:
        # Отправляем всё остальное в OpenRouter
        try:
            bot.send_chat_action(message.chat.id, 'typing')
            resp = client.chat.completions.create(
                model="huggingfaceh4/zephyr-7b-beta",
                messages=[
                    {"role": "system", "content": "Ты — дружелюбный помощник школы гитары SoundMusic из Новосибирска."},
                    {"role": "user", "content": text}
                ]
            )
            answer = resp.choices[0].message.content
            bot.send_message(message.chat.id, answer)
        except Exception as e:
            print("Ошибка OpenRouter:", e)
            bot.send_message(message.chat.id, "⚠️ Что-то пошло не так. Попробуй позже.")

print("Бот с OpenRouter (Zephyr-7B) запущен!")
bot.polling()
