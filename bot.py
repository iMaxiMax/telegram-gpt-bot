import os
import telebot
from telebot import types
import openai

# Получаем токены из переменных окружения
TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

# Проверка на наличие переменных окружения
if not TOKEN or not OPENAI_KEY:
    raise ValueError("❌ Переменные окружения не заданы! Проверь TELEGRAM_TOKEN и OPENAI_API_KEY.")

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
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # ✅ бесплатная модель
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
    except Exception as e:
        print("Ошибка GPT:", e)
        return "⚠️ Не удалось получить ответ от ИИ. Попробуй позже."

# Обработка всех сообщений
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    text = message.text.strip()

    if text == "🎓 О школе":
        bot.send_message(message.chat.id, "🎓 Мы — экспресс-школа гитары SoundMusic, обучаем с нуля и не только. Индивидуально, по шагам, с удовольствием. Знакомься: https://soundmusic54.ru/#menu")
    elif text == "💰 Цены":
        bot.send_message(message.chat.id, "💰 Актуальные цены на обучение: https://soundmusic54.ru/#price")
    elif text == "📝 Как записаться":
        bot.send_message(message.chat.id, "📝 Просто оставь заявку:\nhttps://soundmusic54.ru/#sign\nИли напиши сюда — мы поможем.")
    elif text == "🥇 Уровни учеников":
        bot.send_message(message.chat.id, "🥇 У нас учатся и новички, и профи. Программа подстраивается под твой уровень: https://soundmusic54.ru/top")
    elif text == "🎯 Цели и результат":
        bot.send_message(message.chat.id, "🎯 Мы помогаем достичь цели: научиться играть, писать музыку или выступать: https://soundmusic54.ru/production")
    else:
        bot.send_chat_action(message.chat.id, 'typing')
        gpt_reply = ask_gpt(text)
        bot.send_message(message.chat.id, gpt_reply)

print("Бот с ИИ запущен!")
bot.polling()
