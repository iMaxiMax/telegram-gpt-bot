import os
import telebot
from telebot import types
import openai

# Получаем токены из переменных окружения
TOKEN = os.getenv("8017209296:AAGii8rZFTfgP3NQYVr6bwrRCkJfzU9_c7Q")
OPENAI_KEY = os.getenv("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")

bot = telebot.TeleBot(TOKEN)
openai.api_key = OPENAI_KEY

# Главное меню
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🎓 О школе", "💰 Цены")
    markup.row("📝 Как записаться", "🥇 Уровни учеников")
    markup.row("🎯 Цели и результат")
    return markup

# Ответ на /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(
        message.chat.id,
        "Привет! 👋 Я — навигатор экспресс-школы гитары SOUNDMUSIC.\n\nВыбери интересующий пункт:",
        reply_markup=main_menu()
    )

# GPT-ответ
def ask_gpt(question):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {
                "role": "system",
                "content": (
                    "Ты — честный, тёплый и внимательный помощник школы гитары SoundMusic из Новосибирска. "
                    "Ты отвечаешь по делу, с заботой, без давления, дружелюбно и по-человечески."
                )
            },
            {
                "role": "user",
                "content": question
            }
        ],
        max_tokens=300,
        temperature=0.7
    )
    return response.choices[0].message['content']

# Обработка всех сообщений
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    text = message.text.strip()

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
        try:
            bot.send_chat_action(message.chat.id, 'typing')
            gpt_reply = ask_gpt(text)
            bot.send_message(message.chat.id, gpt_reply)
        except Exception as e:
            print("Ошибка GPT:", e)
            bot.send_message(message.chat.id, "⚠️ Что-то пошло не так. Попробуй ещё раз чуть позже.")

print("Бот с ИИ запущен!")
bot.polling()
