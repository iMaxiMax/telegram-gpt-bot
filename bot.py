import os
import re
import time
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

# Заголовки для обхода защиты от парсинга
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
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

# ================== ПАРСИНГ САЙТА С ЗАЩИТОЙ ОТ БЛОКИРОВОК ================== #
def parse_page_content(soup, url):
    """Извлекает структурированный контент со страницы"""
    content = {}
    
    # Заголовок страницы
    content['title'] = soup.title.string.strip() if soup.title else url
    
    # Основной контент
    main_content = soup.find('main') or soup.find('article') or soup.body
    if main_content:
        # Удаляем ненужные элементы
        for element in main_content(['script', 'style', 'footer', 'header', 'nav', 'form']):
            element.decompose()
        
        # Извлекаем текстовый контент
        content['text'] = main_content.get_text(separator='\n', strip=True)
        content['text'] = re.sub(r'\n{3,}', '\n\n', content['text'])
    
    return content

def load_school_knowledge():
    """Загружает и анализирует информацию со всех страниц сайта"""
    logger.info("🎸 Загрузка знаний о гитарной школе...")
    knowledge = {}
    session = requests.Session()
    
    for page_name, url in PAGES.items():
        try:
            # Используем заголовки и случайные задержки для имитации браузера
            time.sleep(1.5)
            response = session.get(url, headers=HEADERS, timeout=15)
            
            # Проверка на ошибки доступа
            if response.status_code == 403:
                logger.warning(f"Обнаружена блокировка для {url}, пробуем обойти...")
                # Пробуем разные User-Agent
                HEADERS['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15'
                response = session.get(url, headers=HEADERS, timeout=15)
            
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

def find_relevant_sections(query, knowledge_data):
    """Находит релевантные разделы по запросу"""
    query_lower = query.lower()
    results = []
    
    for page_name, page_data in knowledge_data.items():
        # Поиск в основном тексте страницы
        if 'text' in page_data and query_lower in page_data['text'].lower():
            # Находим контекст вхождения
            start_idx = page_data['text'].lower().find(query_lower)
            if start_idx != -1:
                end_idx = min(len(page_data['text']), start_idx + 500)
                snippet = page_data['text'][max(0, start_idx-100):end_idx]
                
                results.append({
                    'source': page_data['title'],
                    'url': page_data['url'],
                    'title': "Релевантная информация",
                    'content': snippet + '...'
                })
    
    return results[:3]  # Не более 3 результатов

def get_contacts_info(knowledge_data):
    """Извлекает контактную информацию со всех страниц"""
    contacts = {'phones': set(), 'addresses': set()}
    phone_pattern = re.compile(r'\+?[78]\s?\(?\d{3}\)?\s?\d{3}[\s-]?\d{2}[\s-]?\d{2}')
    address_pattern = re.compile(r'г\.\s*[А-Яа-я]+\s*,\s*ул\.\s*[А-Яа-я]+\s*,\s*\d+')
    
    for page_data in knowledge_data.values():
        if 'text' in page_data:
            text = page_data['text']
            # Поиск телефонов
            phones = phone_pattern.findall(text)
            if phones:
                contacts['phones'].update(phones)
            
            # Поиск адресов
            addresses = address_pattern.findall(text)
            if addresses:
                contacts['addresses'].update(addresses)
    
    return {
        'phones': list(contacts['phones']),
        'addresses': list(contacts['addresses'])
    }

# ================== ОБРАБОТКА ЗАПРОСОВ ================== #
def generate_answer(query, knowledge_data):
    """Генерирует ответ на основе данных с сайта"""
    # Специальные обработчики для частых запросов
    query_lower = query.lower()
    
    # Поиск контактов
    if any(word in query_lower for word in ['запис', 'контакт', 'телефон', 'адрес']):
        contacts = get_contacts_info(knowledge_data)
        response = "📞 *Контактная информация*\n\n"
        
        if contacts['phones']:
            response += "☎️ *Телефоны:*\n" + "\n".join(contacts['phones']) + "\n\n"
        else:
            response += "ℹ️ Телефоны не найдены на сайте\n\n"
        
        if contacts['addresses']:
            response += "📍 *Адреса:*\n" + "\n".join(contacts['addresses']) + "\n\n"
        else:
            response += "ℹ️ Адреса не найдены на сайте\n\n"
        
        response += "💻 *Сайт:* " + SCHOOL_SITE
        return response
    
    # Общий поиск по сайту
    relevant_sections = find_relevant_sections(query, knowledge_data)
    if relevant_sections:
        response = "🔍 *Найдена информация по вашему запросу:*\n\n"
        for i, section in enumerate(relevant_sections):
            response += f"{i+1}. *{section['title']}* ({section['source']})\n"
            response += f"{section['content']}\n"
            response += f"🔗 [Подробнее]({section['url']})\n\n"
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
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    """Приветственное сообщение о гитарной школе"""
    welcome_msg = (
        "🎵 *Добро пожаловать в SoundMusic54!*\n\n"
        "Я ваш персональный помощник гитарной школы. Чем могу помочь?\n\n"
        "🔹 Узнать информацию о школе\n"
        "🔹 Уточнить контактные данные\n"
        "🔹 Получить сведения о программах обучения\n\n"
        "Просто задайте вопрос о школе или гитаре!\n\n"
        f"Наш сайт: [{SCHOOL_SITE}]({SCHOOL_SITE})"
    )
    
    try:
        bot.send_message(
            message.chat.id,
            welcome_msg,
            parse_mode="Markdown",
            disable_web_page_preview=False
        )
    except Exception:
        bot.send_message(message.chat.id, welcome_msg)

@bot.message_handler(func=lambda m: True)
def handle_guitar_question(message):
    """Обработчик вопросов о гитарной школе"""
    try:
        # Отправка действия "печатает"
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
            "🎸 Здравствуйте! Я помогу с вопросами о гитарной школе SoundMusic54.\n"
            "Пока не могу ответить на ваш вопрос, но вы можете:\n"
            f"- Посетить наш сайт: {SCHOOL_SITE}\n"
            f"- Посмотреть FAQ: {PAGES['faq']}\n\n"
            "Попробуйте задать вопрос иначе!"
        )

# ================== СЕРВИСНЫЕ ФУНКЦИИ ================== #
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

@app.route('/health')
def health_check():
    """Проверка работоспособности сервера"""
    pages_loaded = len(school_knowledge) if school_knowledge else 0
    return {
        "status": "OK",
        "school": "SoundMusic54",
        "pages_loaded": pages_loaded,
        "last_update": datetime.utcnow().isoformat()
    }, 200

# ================== ЗАПУСК СИСТЕМЫ ================== #
def initialize_bot():
    """Инициализация бота с загрузкой знаний о школе"""
    logger.info("🎸 Инициализация гитарного бота...")
    
    # Загрузка знаний о школе
    global school_knowledge
    school_knowledge = load_school_knowledge()
    
    # Запуск периодического обновления знаний
    threading.Thread(target=refresh_knowledge_periodically, daemon=True).start()
    
    # Проверка контактов
    contacts = get_contacts_info(school_knowledge)
    logger.info(f"📞 Найдены контакты: {contacts}")
    
    logger.info("✅ Бот готов к работе!")

def run_bot_safely():
    """Запуск бота с защитой от конфликтов"""
    while True:
        try:
            logger.info("🤖 Запуск Telegram бота...")
            bot.infinity_polling(timeout=90, long_polling_timeout=40, skip_pending=True)
        except Exception as e:
            if "Conflict" in str(e):
                logger.error("⚠️ Обнаружен конфликт: другой экземпляр бота уже запущен. Перезапуск через 10 секунд...")
                time.sleep(10)
            else:
                logger.exception("Критическая ошибка бота:")
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
    run_bot_safely()
