import os
import sys
import requests
from bs4 import BeautifulSoup
import telebot
import re

# --- Настройки ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not TELEGRAM_BOT_TOKEN or not OPENROUTER_API_KEY:
    raise RuntimeError("❌ Не заданы переменные TELEGRAM_BOT_TOKEN или OPENROUTER_API_KEY")

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

HEADERS = {"User-Agent": "Mozilla/5.0"}
BASE_URL = "https://soundmusic54.ru"
PATHS = ["", "production", "fingerstyle", "electricguitar", "shop", "top", "way", "plan", "faq"]
site_contents = {}

def fetch_page(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"Ошибка при загрузке {url}: {e}")
        return None

def load_site():
    print("⚙️ Загружаю сайт...")
    for p in PATHS:
        u = BASE_URL + ("/" + p if p else "")
        html = fetch_page(u)
        text = BeautifulSoup(html, "html.parser").get_text("\n", strip=True) if html else ""
        site_contents[p or "base"] = text
    print("✅ Сайт загружен")

def ask_deepseek(q):
    url = "https://openrouter.ai/api/v1/chat/completions"
    sec = "\n\n".join(f"Раздел '{k}': {v[:800]}" for k, v in site_contents.items() if k in ("base","faq","plan","way"))
    sys_p = ("Ты — помощник SoundMusic, опирайся на сайт. "
             "Если нет точной информации — честно скажи об этом.\n" + sec)
    payload = {"model": "tngtech/deepseek-r1t2-chimera:free",
               "messages":[{"role":"system","content":sys_p},{"role":"user","content":q}],
               "max_tokens":800, "temperature":0.7}
    for model in [
        "tngtech/deepseek-r1t2-chimera:free",
        "togethercomputer/stripedhyena-hessian:free",
        "mistralai/mistral-7b-instruct:free"
    ]:
        payload["model"] = model
        try:
            r = requests.post(url, headers={"Authorization":f"Bearer {OPENROUTER_API_KEY}","Content-Type":"application/json"}, json=payload, timeout=20)
            if r.status_code == 200:
                d = r.json()
                txt = d.get("choices",[{}])[0].get("message",{}).get("content","").strip()
                return txt or "⚠️ Пустой ответ."
            if r.status_code in (400,429):
                print(f"❌ Модель {model} вернула {r.status_code}, пробуем следующую")
                continue
        except Exception as e:
            print(f"❌ Ошибка {model}: {e}")
    return "⚠️ Все модели недоступны, попробуйте позже."

def fmt_md(text):
    t = text.replace("__","*").replace("**","*")
    return re.sub(r'<br\s*/?>','\n',t,flags=re.I)

@bot.message_handler(commands=['start','help'])
def cmd_start(m):
    bot.send_message(m.chat.id, "Привет! Я — помощник SoundMusic. Задавай вопросы!")

@bot.message_handler(func=lambda m: True)
def msg(m):
    q = m.text.strip()
    if not q:
        bot.send_message(m.chat.id, "Пожалуйста, задай вопрос.")
        return
    bot.send_chat_action(m.chat.id, 'typing')
    a = ask_deepseek(q)
    a = fmt_md(a)
    for i in range(0, len(a), 4000):
        bot.send_message(m.chat.id, a[i:i+4000], parse_mode="Markdown")

def check_conflict():
    try:
        bot.get_updates(offset=-1, timeout=1)
    except telebot.apihelper.ApiTelegramException as e:
        if "409" in str(e):
            print("❗ Уже запущен другой бот → 409 Conflict. Выход.")
            sys.exit(0)
        else:
            raise

if __name__ == "__main__":
    check_conflict()
    load_site()
    print("🚀 Бот запущен!")
    bot.infinity_polling()
