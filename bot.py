import os
import re
import time
import random
import logging
import threading
import requests
from bs4 import BeautifulSoup
import telebot
from flask import Flask
from datetime import datetime
from urllib.parse import urljoin
import json

# ================== КОНФИГУРАЦИЯ САЙТА ================== #
SCHOOL_SITE = "https://soundmusic54.ru"
PAGES = {
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

# Заголовки для обхода защиты
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
    'Connection': 'keep-alive',
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
logger = logging.getLogger('SoundMusic54Bot')
logger.setLevel(logging.DEBUG if os.getenv('DEBUG', 'false').lower() == 'true' else logging.INFO)

# ================== ИНИЦИАЛИЗАЦИЯ ================== #
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not BOT_TOKEN:
    logger.critical("❌ TELEGRAM_BOT_TOKEN не установен!")
    raise EnvironmentError("Токен бота не найден")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# Глобальное хранилище знаний о школе
school_knowledge = {}
lock = threading.Lock()

# ================== ПАРСИНГ САЙТА ================== #
def parse_page_content(soup, url):
    """Извлекает контент со страницы"""
    content = {}
    
    # Заголовок страницы
    content['title'] = soup.title.string.strip() if soup.title else url
    
    # Основной контент
    main_content = soup.find('main') or soup.find('article') or soup.body
    if main_content:
        # Удаляем ненужные элементы
        for element in main_content(['script', 'style', 'footer', 'header', 'nav']):
            element.decompose()
        
        # Извлекаем текстовый контент
        content['text'] = main_content.get_text(separator='\n', strip=True)
        content['text'] = re.sub(r'\n{3,}', '\n\n', content['text'])
    
    return content

def load_school_knowledge():
    """Загружает информацию со страниц сайта"""
    logger.info("🎸 Загрузка знаний о гитарной школе...")
    knowledge = {}
    session = requests.Session()
    
    for page_name, url in PAGES.items():
        try:
            # Случайная задержка
            time.sleep(random.uniform(1.0, 2.5))
            
            # Используем разные User-Agent
            headers = HEADERS.copy()
            headers['User-Agent'] = random.choice([
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
                'Mozilla/5.0 (X11; Linux x86_64)'
            ])
            
            response = session.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            page_content = parse_page_content(soup, url)
            page_content['url'] = url
            knowledge[page_name] = page_content
            
            logger.info(f"✅ Загружено: {page_name} - {page_content['title']}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки {url}: {str(e)}")
            knowledge[page_name] = {
                'url': url,
                'title': page_name,
                'text': f"Информация временно недоступна. Посетите: {url}"
            }
    
    return knowledge

def find_relevant_info(query, knowledge_data):
    """Находит релевантную информацию по запросу"""
    query_lower = query.lower()
    results = []
    
    for page_name, page_data in knowledge_data.items():
        # Поиск в тексте страницы
        if 'text' in page_data and query_lower in page_data['text'].lower():
            # Находим контекст вхождения
            start_idx = page_data['text'].lower().find(query_lower)
            if start_idx != -1:
                end_idx = min(len(page_data['text']), start_idx + 300)
                snippet = page_data['text'][max(0, start_idx-100):end_idx]
                
                results.append({
                    'source': page_data['title'],
                    'url': page_data['url'],
                    'content': snippet + '...'
                })
    
    return results[:2]  # Не более 2 результатов

# ================== ОБРАБОТКА ЗАПРОСОВ ================== #
def generate_answer(query, knowledge_data):
    """Генерирует ответ на основе данных с сайта"""
    # Поиск релевантной информации
    relevant_info = find_relevant_info(query, knowledge_data)
    
    if relevant_info:
        response = "🔍 *Найдена информация по вашему запросу:*\n\n"
        for i, info in enumerate(relevant_info):
            response += f"{i+1}. [{info['source']}]({info['url']})\n"
            response += f"{info['content']}\n\n"
        return response
    
    # Если ничего не найдено
    return (
        "🎸 *SoundMusic54 - экспресс-школа игры на гитаре*\n\n"
        "К сожалению, я не нашел информации по вашему запросу.\n"
        "Попробуйте задать вопрос иначе или посетите наш сайт:\n"
        f"{SCHOOL_SITE}\n\n"
        "Вы также можете посмотреть:\n"
        f"- [Главная страница]({PAGES['main']})\n"
        f"- [Частые вопросы]({PAGES['faq']})"
    )

# ================== ОБРАБОТЧИКИ TELEGRAM ================== #
@app.route('/')
def home():
    return "🤖 Бот гитарной школы SoundMusic54 активен"

@app.route('/health')
def health_check():
    return json.dumps({
        "status": "OK",
        "pages_loaded": len(school_knowledge),
        "timestamp": datetime.now().isoformat()
    }), 200

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    """Приветственное сообщение"""
    welcome_msg = (
        "🎵 *Добро пожаловать в SoundMusic54!*\n\n"
        "Я ваш персональный помощник гитарной школы. Чем могу помочь?\n\n"
        "🔹 Узнать информацию о школе\n"
        "🔹 Уточнить контактные данные\n"
        "🔹 Получить сведения о программах обучения\n\n"
        "Просто задайте вопрос о школе или гитаре!\n\n"
        f"Наш сайт: [{SCHOOL_SITE}]({SCHOOL_SITE})"
    )
    
    bot.send_message(
        message.chat.id,
        welcome_msg,
        parse_mode="Markdown",
        disable_web_page_preview=False
    )

@bot.message_handler(func=lambda m: True)
def handle_question(message):
    """Обработчик вопросов"""
    try:
        bot.send_chat_action(message.chat.id, 'typing')
        
        # Получаем ответ на основе данных с сайта
        with lock:
            response = generate_answer(message.text, school_knowledge)
        
        # Отправляем ответ
        bot.send_message(
            message.chat.id,
            response,
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
        
    except Exception as e:
        logger.exception("Ошибка обработки вопроса")
        bot.send_message(
            message.chat.id,
            "🎸 К сожалению, возникла ошибка при обработке запроса.\n"
            "Попробуйте задать вопрос иначе или посетите наш сайт:\n"
            f"{SCHOOL_SITE}"
        )

# ================== ЗАПУСК СИСТЕМЫ ================== #
def initialize_bot():
    """Инициализация бота"""
    logger.info("🎸 Инициализация гитарного бота...")
    
    # Загрузка знаний о школе
    global school_knowledge
    school_knowledge = load_school_knowledge()
    
    logger.info("✅ Бот готов к работе!")

def run_bot():
    """Запуск бота с защитой от конфликтов"""
    while True:
        try:
            logger.info("🤖 Запуск Telegram бота...")
            # Удаляем вебхук перед запуском polling
            bot.remove_webhook()
            time.sleep(1)
            
            # Запускаем polling с увеличенным таймаутом
            bot.polling(none_stop=True, interval=1, timeout=60)
            
        except Exception as e:
            if "Conflict" in str(e):
                logger.error("⚠️ Обнаружен конфликт: перезапуск через 30 секунд...")
                time.sleep(30)
            else:
                logger.exception(f"Критическая ошибка бота: {str(e)}")
                time.sleep(10)

if __name__ == '__main__':
    initialize_bot()
    
    # Запуск Flask в отдельном потоке
    flask_thread = threading.Thread(
        target=lambda: app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False),
        daemon=True
    )
    flask_thread.start()
    
    # Запуск бота с защитой от конфликтов
    run_bot()
