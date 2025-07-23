import os
import requests

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

def ask_gpt(question: str) -> str:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        # Можно добавить для рейтинга, если хочешь
        # "HTTP-Referer": "https://soundmusic54.ru",
        # "X-Title": "SoundMusic Bot"
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
