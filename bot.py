import os
import telebot
from telebot import types
from openai import OpenAI  # Если хочешь, заменю на openrouter_sdk

# Получаем токены из переменных окружения (без хардкода!)
TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

if not TOKEN or not OPENAI_KEY:
    raise ValueError("❌ Задайте TELEGRAM_TOKEN и OPENAI_API_KEY в переменных окружения!")

bot = telebot.TeleBot(TOKEN)
client = OpenAI(api_key=OPENAI_KEY)

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
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {
                "role": "system",
                "content": (
                    "Ты — честный, тёплый и внимательный помощник школы гитары SoundMusic из Новосибирска. "
                    "Ты отвечаешь по делу, с заботой, без давления, дружелюбно и по-человечески."
                )
            },
            {"role": "user", "content": question}
        ],
        max_tokens=300,
        temperature=0.7
    )
    return response.choices[0].message.content

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    text = message.text.strip()

    if text == "🎓 О школе":
        bot.send_message(message.chat.id, "🎓 Мы — экспресс-школа гитары soundmusic, обучаем с нуля и не только. Индивидуально, по шагам, с удовольствием. Подробнее: https://soundmusic54.ru/#menu")
    elif text == "💰 Цены":
        bot.send_message(message.chat.id, "💰 Актуальные цены: https://soundmusic54.ru/#price")
    elif text == "📝 Как записаться":
        bot.send_message(message.chat.id, "📝 Заявка на сайте: https://soundmusic54.ru/#sign\nИли напиши здесь, поможем.")
    elif text == "🥇 Уровни учеников":
        bot.send_message(message.chat.id, "🥇 Программа под твой уровень: https://soundmusic54.ru/top")
    elif text == "🎯 Цели и результат":
        bot.send_message(message.chat.id, "🎯 Помогаем достичь цели: https://soundmusic54.ru/production")
    else:
        try:
            bot.send_chat_action(message.chat.id, 'typing')
            gpt_reply = ask_gpt(text)
            bot.send_message(message.chat.id, gpt_reply)
        except Exception as e:
            print("Ошибка GPT:", e)
            bot.send_message(message.chat.id, "⚠️ Что-то пошло не так. Попробуй позже.")

print("Бот с ИИ запущен!")
bot.polling()
