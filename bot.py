import os
import telebot
import requests

# Получаем токены из переменных окружения
TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not TOKEN or not OPENROUTER_API_KEY:
    raise ValueError("❌ Переменные окружения не заданы! Проверь TELEGRAM_TOKEN и OPENROUTER_API_KEY.")

bot = telebot.TeleBot(TOKEN)

# Функция для запроса к OpenRouter (Zephyr-7B-beta)
def ask_openrouter(question):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "model": "zephyr-7b-beta",
        "messages": [
            {
                "role": "system",
                "content": (
                    "Ты — честный, тёплый и внимательный помощник школы гитары SoundMusic из Новосибирска. "
                    "Отвечай дружелюбно, по делу, с заботой, не слишком многословно."
                )
            },
            {
                "role": "user",
                "content": question
            }
        ],
        "max_tokens": 300,
        "temperature": 0.7
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        resp_json = response.json()
        return resp_json['choices'][0]['message']['content']
    else:
        print(f"Ошибка OpenRouter: {response.status_code} - {response.text}")
        return "⚠️ Извините, сейчас я не могу ответить. Попробуйте позже."

# Главное меню
from telebot import types
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
    # Жёстко заданные ответы на меню
    if text == "🎓 О школе":
        bot.send_message(message.chat.id, "🎓 Мы — экспресс-школа гитары soundmusic, обучаем с нуля и не только. Индивидуально, по шагам, с удовольствием. Подробнее: https://soundmusic54.ru/#menu")
    elif text == "💰 Цены":
        bot.send_message(message.chat.id, "💰 Актуальные цены на обучение: https://soundmusic54.ru/#price")
    elif text == "📝 Как записаться":
        bot.send_message(message.chat.id, "📝 Оставь заявку на сайте или напиши сюда, мы поможем: https://soundmusic54.ru/#sign")
    elif text == "🥇 Уровни учеников":
        bot.send_message(message.chat.id, "🥇 Программа подстраивается под твой уровень: https://soundmusic54.ru/top")
    elif text == "🎯 Цели и результат":
        bot.send_message(message.chat.id, "🎯 Помогаем научиться играть, писать музыку и выступать: https://soundmusic54.ru/production")
    else:
        try:
            bot.send_chat_action(message.chat.id, 'typing')
            answer = ask_openrouter(text)
            bot.send_message(message.chat.id, answer)
        except Exception as e:
            print("Ошибка OpenRouter:", e)
            bot.send_message(message.chat.id, "⚠️ Что-то пошло не так. Попробуй позже.")

print("Бот с OpenRouter (Zephyr-7B-beta) запущен!")
bot.polling()
