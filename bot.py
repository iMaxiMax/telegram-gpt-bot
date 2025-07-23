import os
import telebot
import requests
from telebot.apihelper import ApiTelegramException
from dotenv import load_dotenv

load_dotenv()  # Загружаем переменные из .env

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not TELEGRAM_BOT_TOKEN:
    raise Exception("❌ TELEGRAM_BOT_TOKEN не задан!")

if not OPENROUTER_API_KEY:
    raise Exception("❌ OPENROUTER_API_KEY не задан!")

print("✅ Запуск Telegram-бота...")
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)


def ask_gpt(question: str) -> str:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        # "HTTP-Referer": "https://soundmusic54.ru",
        # "X-Title": "SoundMusic Bot"
    }

    payload = {
        "model": "tngtech/deepseek-r1t2-chimera:free",
        "messages": [
            {
                "role": "system",
                "content": "Ты — тёплый, честный помощник школы SoundMusic. Отвечай понятно, дружелюбно и полезно.",
            },
            {
                "role": "user",
                "content": question
            }
        ],
        "max_tokens": 300,
        "temperature": 0.7
    }

    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload
        )

        if response.ok:
            data = response.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "⚠️ Пустой ответ.")
        else:
            print("❌ Ошибка OpenRouter:", response.status_code, response.text)
            return "⚠️ Ошибка сервиса. Попробуй позже."

    except Exception as e:
        print("❌ Исключение при обращении к OpenRouter:", str(e))
        return "⚠️ Что-то пошло не так. Попробуй позже."


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    text = message.text.strip()
    if not text:
        bot.send_message(message.chat.id, "Пожалуйста, напиши что-нибудь.")
        return

    try:
        answer = ask_gpt(text)
        bot.send_message(message.chat.id, answer)
    except ApiTelegramException as e:
        if e.result_json.get('description') == 'Forbidden: bot was blocked by the user':
            print(f"🚫 Пользователь {message.chat.id} заблокировал бота.")
        else:
            print(f"❌ Ошибка Telegram API: {e}")
            raise e
    except Exception as e:
        print(f"❌ Общая ошибка: {e}")
        bot.send_message(message.chat.id, "⚠️ Что-то пошло не так. Попробуй позже.")


if __name__ == "__main__":
    print("🚀 Бот с DeepSeek запущен!")
    bot.polling(none_stop=True)
