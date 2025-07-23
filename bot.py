import os
import telebot
from telebot import types
from openrouter_sdk import OpenRouter  # ← правильный импорт SDK

# Получаем токены
TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")

if not TOKEN or not OPENROUTER_KEY:
    raise ValueError("❌ Проверь TELEGRAM_TOKEN и OPENROUTER_API_KEY!")

bot = telebot.TeleBot(TOKEN)
client = OpenRouter(api_key=OPENROUTER_KEY)

# Меню
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🎓 О школе", "💰 Цены")
    markup.row("📝 Как записаться", "🥇 Уровни учеников")
    markup.row("🎯 Цели и результат")
    return markup

# Старт
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(
        message.chat.id,
        "Привет! 👋 Я — навигатор экспресс-школы гитары SOUNDMUSIC.\n\nВыбери интересующий пункт:",
        reply_markup=main_menu()
    )

# Ответ от OpenRouter
def ask_openrouter(question):
    response = client.chat.completions.create(
        model="huggingfaceh4/zephyr-7b-beta",
        messages=[
            {"role": "system", "content": "Ты — тёплый и честный помощник школы гитары SoundMusic из Новосибирска. Отвечай понятно, дружелюбно, по-человечески."},
            {"role": "user", "content": question}
        ],
        max_tokens=300,
        temperature=0.7
    )
    return response.choices[0].message.content

# Обработка сообщений
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    text = message.text.strip()

    if text == "🎓 О школе":
        bot.send_message(message.chat.id, "🎓 Мы — экспресс-школа гитары: https://soundmusic54.ru/#menu")
    elif text == "💰 Цены":
        bot.send_message(message.chat.id, "💰 Актуальные цены: https://soundmusic54.ru/#price")
    elif text == "📝 Как записаться":
        bot.send_message(message.chat.id, "📝 Заявка: https://soundmusic54.ru/#sign")
    elif text == "🥇 Уровни учеников":
        bot.send_message(message.chat.id, "🥇 Подходит и новичкам, и профи: https://soundmusic54.ru/top")
    elif text == "🎯 Цели и результат":
        bot.send_message(message.chat.id, "🎯 Результаты учеников: https://soundmusic54.ru/production")
    else:
        try:
            bot.send_chat_action(message.chat.id, 'typing')
            reply = ask_openrouter(text)
            bot.send_message(message.chat.id, reply)
        except Exception as e:
            print("Ошибка OpenRouter:", e)
            bot.send_message(message.chat.id, "⚠️ Что-то пошло не так. Попробуй позже.")

print("Бот с OpenRouter (Zephyr-7B-beta) запущен!")
bot.polling()
