import os
import re
import time
import logging
import threading
import requests
import telebot
from flask import Flask
from functools import wraps
from telebot import formatting
from telebot.apihelper import ApiTelegramException
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin

# ================== КОНФИГУРАЦИЯ ГИТАРНОЙ ШКОЛЫ ================== #
SCHOOL_SITE = "https://soundmusic54.ru"
SCHOOL_PAGES = {
    "main": SCHOOL_SITE,
    "production": urljoin(SCHOOL_SITE, "production"),
    "fingerstyle": urljoin(SCHOOL_SITE, "fingerstyle"),
    "electricguitar": urljoin(SCHOOL_SITE, "electricguitar"),
    "shop": urljoin(SCHOOL_SITE, "shop"),
    "top": urljoin(SCHOOL_SITE, "top"),
    "way": urljoin(SCHOOL_SITE, "way"),
    "plan": urljoin(SCHOOL_SITE, "plan"),
    "faq": urljoin(SCHOOL_SITE, "faq")
}

# ================== НАСТРОЙКА ЛОГГИРОВАНИЯ ================== #
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('guitar_bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger('GuitarSchoolBot')
logger.setLevel(logging.DEBUG if os.getenv('DEBUG') else logging.INFO)

# ================== ИНИЦИАЛИЗАЦИЯ ================== #
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not BOT_TOKEN:
    logger.critical("❌ TELEGRAM_BOT_TOKEN не установен!")
    raise EnvironmentError("Токен бота не найден")

bot = telebot.TeleBot(BOT_TOKEN, threaded=True, num_threads=4)
app = Flask(__name__)

# Глобальное хранилище знаний о школе
school_knowledge = {}
lock = threading.Lock()

# ================== СИСТЕМА ЗНАНИЙ О ШКОЛЕ ================== #
def load_school_knowledge():
    """Загружает и парсит информацию со всех страниц сайта школы"""
    logger.info("🎸 Загрузка знаний о гитарной школе...")
    knowledge = {}
    
    for page_name, url in SCHOOL_PAGES.items():
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Удаляем ненужные элементы
            for element in soup(['script', 'style', 'footer', 'header', 'nav']):
                element.decompose()
            
            # Извлекаем основной контент
            content = soup.find('main') or soup.find('article') or soup.find('div', class_='content')
            
            if not content:
                content = soup.body
            
            # Очистка и форматирование текста
            text = content.get_text(separator='\n', strip=True)
            text = re.sub(r'\n{3,}', '\n\n', text)
            
            knowledge[page_name] = {
                'url': url,
                'title': soup.title.string if soup.title else page_name,
                'content': text[:15000]  # Ограничение объема
            }
            
            logger.info(f"✅ Загружено: {page_name} ({len(text)} символов)")
            
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки {url}: {str(e)}")
            knowledge[page_name] = {
                'url': url,
                'title': page_name,
                'content': f"Информация временно недоступна. Посетите: {url}"
            }
    
    return knowledge

def get_relevant_knowledge(query: str) -> str:
    """Находит наиболее релевантную информацию о школе по запросу"""
    query = query.lower()
    relevant_info = []
    
    # Поиск по всем страницам
    for name, data in school_knowledge.items():
        content = data['content'].lower()
        
        # Простой поиск по ключевым словам
        if query in content:
            # Находим контекст вокруг ключевого слова
            start_idx = max(0, content.find(query) - 100)
            end_idx = min(len(content), content.find(query) + len(query) + 300)
            snippet = data['content'][start_idx:end_idx]
            
            relevant_info.append(
                f"📚 Из раздела '{data['title']}':\n{snippet}...\n"
                f"🔗 Подробнее: {data['url']}"
            )
    
    # Если найдена релевантная информация
    if relevant_info:
        return "\n\n".join(relevant_info[:3])  # Не более 3 фрагментов
    
    # Если ничего не найдено, возвращаем общую информацию
    return (
        "🎸 Информация о гитарной школе SoundMusic54:\n"
        f"- Основной сайт: {SCHOOL_PAGES['main']}\n"
        f"- Программы обучения: {SCHOOL_PAGES['production']}\n"
        f"- FAQ: {SCHOOL_PAGES['faq']}\n\n"
        "Задайте уточняющий вопрос о направлениях обучения, "
        "преподавателях или стоимости занятий."
    )

def refresh_knowledge_periodically():
    """Периодически обновляет знания о школе"""
    while True:
        time.sleep(24 * 3600)  # Обновление раз в сутки
        try:
            with lock:
                global school_knowledge
                school_knowledge = load_school_knowledge()
            logger.info("🔄 Знания о школе обновлены!")
        except Exception as e:
            logger.error(f"Ошибка обновления знаний: {str(e)}")

# ================== ИНТЕГРАЦИЯ С DEEPSEEK ================== #
def ask_deepseek(question: str) -> str:
    """Запрашивает ответ у DeepSeek с контекстом о гитарной школе"""
    # Получаем релевантную информацию о школе
    school_info = get_relevant_knowledge(question)
    
    # Формируем промпт с контекстом о школе
    system_prompt = (
        "Ты — помощник гитарной школы SoundMusic54. Отвечай на вопросы, "
        "используя информацию о школе. Если вопрос не о школе или гитаре, "
        "вежливо сообщи о специализации. Вот информация о школе:\n\n"
        f"{school_info}\n\n"
        "Ответ должен быть полезным, мотивирующим и профессиональным."
    )
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ],
        "temperature": 0.7,
        "max_tokens": 1200
    }
    
    try:
        response = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {os.getenv('DEEPSEEK_API_KEY')}"},
            timeout=25
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    
    except Exception as e:
        logger.error(f"DeepSeek error: {str(e)}")
        return (
            "🎸 Здравствуйте! Я помогу с вопросами о гитарной школе SoundMusic54.\n\n"
            f"Пока я не могу обработать ваш запрос, но вот полезная информация:\n\n"
            f"{school_info}"
        )

# ================== ОБРАБОТЧИКИ TELEGRAM ================== #
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    """Приветственное сообщение о гитарной школе"""
    welcome_msg = (
        "🎵 *Добро пожаловать в SoundMusic54!*\n\n"
        "Я ваш персональный помощник гитарной школы. Чем могу помочь?\n\n"
        "🔹 Узнайте о наших программах обучения\n"
        "🔹 Получите консультацию по выбору курса\n"
        "🔹 Узнайте о преподавателях\n"
        "🔹 Получите информацию о стоимости\n\n"
        "Просто задайте вопрос о школе, гитаре или обучении!\n\n"
        "Посетите наш сайт: [soundmusic54.ru](https://soundmusic54.ru)"
    )
    
    try:
        bot.send_message(
            message.chat.id,
            welcome_msg,
            parse_mode="Markdown",
            disable_web_page_preview=False
        )
    except ApiTelegramException:
        bot.send_message(message.chat.id, welcome_msg)

@bot.message_handler(commands=['programs'])
def show_programs(message):
    """Показывает программы обучения"""
    try:
        programs_info = (
            "🎸 *Наши программы обучения:*\n\n"
            f"• [Акустическая гитара]({SCHOOL_PAGES['production']})\n"
            f"• [Фингерстайл]({SCHOOL_PAGES['fingerstyle']})\n"
            f"• [Электрогитара]({SCHOOL_PAGES['electricguitar']})\n\n"
            "Выберите направление для подробной информации!"
        )
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Все программы", url=SCHOOL_PAGES['production']))
        markup.add(types.InlineKeyboardButton("FAQ", url=SCHOOL_PAGES['faq']))
        
        bot.send_message(
            message.chat.id,
            programs_info,
            parse_mode="Markdown",
            reply_markup=markup
        )
    except Exception as e:
        logger.error(f"Ошибка показа программ: {str(e)}")
        bot.send_message(
            message.chat.id,
            "Посмотрите наши программы на сайте: " + SCHOOL_PAGES['production']
        )

@bot.message_handler(func=lambda m: True)
def handle_guitar_question(message):
    """Обработчик вопросов о гитарной школе"""
    try:
        # Отправка действия "печатает"
        bot.send_chat_action(message.chat.id, 'typing')
        
        # Получение ответа с учетом знаний о школе
        response = ask_deepseek(message.text)
        
        # Улучшенная обработка ответа
        formatted_response = format_guitar_response(response)
        
        # Отправка ответа
        send_safe_message(message.chat.id, formatted_response, reply_to=message.message_id)
        
    except Exception as e:
        logger.exception("Ошибка обработки вопроса")
        bot.send_message(
            message.chat.id,
            "🎸 Здравствуйте! Я помогу с вопросами о гитарной школе SoundMusic54.\n"
            "Пока не могу ответить на ваш вопрос, но вы можете:\n"
            f"- Посетить наш сайт: {SCHOOL_PAGES['main']}\n"
            f"- Посмотреть FAQ: {SCHOOL_PAGES['faq']}\n\n"
            "Попробуйте задать вопрос иначе или свяжитесь с нами напрямую!"
        )

# ================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ================== #
def format_guitar_response(text: str) -> str:
    """Форматирует ответ с акцентом на гитарную тематику"""
    # Добавляем гитарную тематику в ответ
    guitar_phrases = [
        "🎸 Ваш звук начинается здесь!",
        "🎶 Добро пожаловать в мир музыки!",
        "🔥 Зажигаем новые таланты!",
        "🎵 SoundMusic54 - твой путь к мастерству!"
    ]
    
    # Добавляем случайную музыкальную фразу
    import random
    if random.random() > 0.7:  # 30% вероятности
        text += f"\n\n{random.choice(guitar_phrases)}"
    
    # Добавляем ссылку на сайт
    if SCHOOL_SITE not in text:
        text += f"\n\n🔗 Больше информации: {SCHOOL_PAGES['main']}"
    
    return text

def send_safe_message(chat_id, text, reply_to=None):
    """Безопасная отправка сообщений с обработкой ошибок"""
    try:
        # Разбиваем длинные сообщения
        if len(text) > 3000:
            parts = [text[i:i+3000] for i in range(0, len(text), 3000)]
            for part in parts:
                bot.send_message(chat_id, part, reply_to_message_id=reply_to)
                time.sleep(0.3)
                reply_to = None  # Только первое сообщение будет ответом
        else:
            bot.send_message(chat_id, text, reply_to_message_id=reply_to)
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения: {str(e)}")
        # Попытка отправить без форматирования
        try:
            clean_text = re.sub(r'[*_`[]]', '', text)[:4000]
            bot.send_message(chat_id, clean_text, reply_to_message_id=reply_to)
        except:
            bot.send_message(
                chat_id,
                "🎸 Ваш запрос получен! Подробнее на сайте: " + SCHOOL_PAGES['main'],
                reply_to_message_id=reply_to
            )

# ================== ЗАПУСК СИСТЕМЫ ================== #
def initialize_bot():
    """Инициализация бота с загрузкой знаний о школе"""
    logger.info("🎸 Инициализация гитарного бота...")
    
    # Загрузка знаний о школе
    global school_knowledge
    school_knowledge = load_school_knowledge()
    
    # Запуск периодического обновления знаний
    threading.Thread(target=refresh_knowledge_periodically, daemon=True).start()
    
    # Основные команды
    logger.info("✅ Бот готов к работе!")

@app.route('/health')
def health_check():
    return {
        "status": "OK",
        "school": "SoundMusic54",
        "pages_loaded": len(school_knowledge),
        "last_update": datetime.utcnow().isoformat()
    }, 200

if __name__ == '__main__':
    initialize_bot()
    
    # Запуск Flask в отдельном потоке
    flask_thread = threading.Thread(
        target=lambda: app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False),
        daemon=True
    )
    flask_thread.start()
    
    # Запуск бота с обработкой ошибок
    while True:
        try:
            logger.info("🤖 Запуск Telegram бота...")
            bot.infinity_polling(timeout=90, long_polling_timeout=40)
        except Exception as e:
            logger.critical(f"КРИТИЧЕСКАЯ ОШИБКА: {str(e)}")
            logger.info("Перезапуск через 15 секунд...")
            time.sleep(15)
