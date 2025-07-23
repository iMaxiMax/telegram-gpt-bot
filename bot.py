import os
import telebot
from telebot import types
import requests
from dotenv import load_dotenv
from telebot.apihelper import ApiTelegramException

# Загружаем переменные из окружения
load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not TOKEN or not OPENROUTER_API_KEY:
    raise ValueError("❌ TELEGRAM_TOKEN или OPENROUTER_API_KEY не заданы!")

bot = telebot.TeleBot(TOKEN)

# Главное меню
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🎓 О школе", "💰 Цены")
    markup.row("📝 Как записаться", "🥇 Уровни учеников")
    markup.row("🎯 Цели и результат")
    return markup

# Стартовое сообщение
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(
        message.chat.id,
        "Привет! 👋 Я — навигатор экспресс-школы гитары SOUNDMUSIC.\n\nВыбери пункт:",
        reply_markup=main_menu()
    )

# Запрос к OpenRouter / DeepSeek
def ask_gpt(question: str) -> str:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "tngtech/deepseek-r1t2-chimera:free",
        "messages": [
            {"role": "system", "content": "Ты — тёплый, честный помощник SoundMusic. Отвечай понятно и доброжелательно."},
            {"role": "user", "content": question}
        ],
        "max_tokens": 100,
        "temperature": 0.7
    }

    try:
        resp = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
        if resp.ok:
            data = resp.json()
            # Безопасно достаём ответ
            choices = data.get("choices")
            if choices and isinstance(choices, list):
                content = choices[0].get("message", {}).get("content", "").strip()
                return content if content else "⚠️ Ответ пустой. Попробуй переформулировать вопрос."
            else:
                print("⚠️ Unexpected format:", data)
                return "⚠️ Неожиданный ответ от ИИ. Попробуй снова позже."
        else:
            print("❌ Ошибка OpenRouter:", resp.status_code, resp.text)
            return "⚠️ Ошибка сервиса. Попробуй позже."
    except Exception as e:
        print("❌ Ошибка при обращении к OpenRouter:", str(e))
        return "⚠️ Не удалось связаться с ИИ. Попробуй позже."

# Обработка всех сообщений
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
        try:
            bot.send_message(message.chat.id, responses[text])
        except ApiTelegramException as e:
            if e.result_json.get('description') == 'Forbidden: bot was blocked by the user':
                print(f"Пользователь {message.chat.id} заблокировал бота.")
            else:
                raise e
    else:
        bot.send_chat_action(message.chat.id, 'typing')
        reply = ask_gpt(text)
        if reply:
            try:
                bot.send_message(message.chat.id, reply, reply_markup=main_menu())
            except ApiTelegramException as e:
                if e.result_json.get('description') == 'Forbidden: bot was blocked by the user':
                    print(f"Пользователь {message.chat.id} заблокировал бота.")
                else:
                    raise e

print("🚀 Бот с DeepSeek запущен!")
bot.infinity_polling()
