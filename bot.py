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

# ================== ПАРСИНГ САЙТА ================== #
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
    
    # Извлечение ключевых секций
    sections = {}
    headers = main_content.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
    for header in headers:
        section_title = header.get_text().strip()
        section_content = []
        next_element = header.next_sibling
        
        while next_element and next_element.name not in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            if next_element.name and next_element.get_text().strip():
                section_content.append(next_element.get_text().strip())
            next_element = next_element.next_sibling
        
        sections[section_title] = '\n'.join(section_content)
    
    content['sections'] = sections
    
    # Извлечение контактов
    contacts = {}
    phone_pattern = re.compile(r'\+?[78]\s?\(?\d{3}\)?\s?\d{3}[\s-]?\d{2}[\s-]?\d{2}')
    address_pattern = re.compile(r'г\.\s*[А-Яа-я]+\s*,\s*ул\.\s*[А-Яа-я]+\s*,\s*\d+')
    
    for text in [content.get('text', '')] + list(sections.values()):
        phones = phone_pattern.findall(text)
        addresses = address_pattern.findall(text)
        
        if phones:
            contacts['phones'] = list(set(phones))
        if addresses:
            contacts['addresses'] = list(set(addresses))
    
    if contacts:
        content['contacts'] = contacts
    
    return content

def load_school_knowledge():
    """Загружает и анализирует информацию со всех страниц сайта"""
    logger.info("🎸 Загрузка знаний о гитарной школе...")
    knowledge = {}
    
    for page_name, url in PAGES.items():
        try:
            response = requests.get(url, timeout=15)
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
    
    # Сохраняем знания в файл для отладки
    with open('school_knowledge.json', 'w', encoding='utf-8') as f:
        json.dump(knowledge, f, ensure_ascii=False, indent=2)
    
    return knowledge

def find_relevant_sections(query, knowledge_data):
    """Находит релевантные разделы по запросу"""
    query_lower = query.lower()
    results = []
    
    for page_name, page_data in knowledge_data.items():
        # Поиск в заголовках разделов
        for section_title, section_content in page_data.get('sections', {}).items():
            if query_lower in section_title.lower():
                results.append({
                    'source': page_data['title'],
                    'url': page_data['url'],
                    'title': section_title,
                    'content': section_content[:1000] + '...' if len(section_content) > 1000 else section_content
                })
        
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
    
    for page_data in knowledge_data.values():
        if 'contacts' in page_data:
            if 'phones' in page_data['contacts']:
                contacts['phones'].update(page_data['contacts']['phones'])
            if 'addresses' in page_data['contacts']:
                contacts['addresses'].update(page_data['contacts']['addresses'])
    
    return {
        'phones': list(contacts['phones']),
        'addresses': list(contacts['addresses'])
    }

# ================== ОБРАБОТКА ЗАПРОСОВ ================== #
def generate_answer(query, knowledge_data):
    """Генерирует ответ на основе данных с сайта"""
    # Специальные обработчики для частых запросов
    query_lower = query.lower()
    
    if any(word in query_lower for word in ['цена', 'стоимость', 'тариф', 'оплат']):
        price_info = find_relevant_sections("стоимость", knowledge_data)
        if price_info:
            response = "🎸 *Стоимость обучения*\n\n"
            for info in price_info:
                response += f"🔹 *{info['title']}*\n{info['content']}\n\n"
            response += f"🔗 Подробнее: {price_info[0]['url']}"
            return response
    
    if any(word in query_lower for word in ['запис', 'контакт', 'телефон', 'адрес']):
        contacts = get_contacts_info(knowledge_data)
        response = "📞 *Контактная информация*\n\n"
        
        if contacts['phones']:
            response += "☎️ *Телефоны:*\n" + "\n".join(contacts['phones']) + "\n\n"
        if contacts['addresses']:
            response += "📍 *Адреса:*\n" + "\n".join(contacts['addresses']) + "\n\n"
        
        response += "💻 *Сайт:* " + SCHOOL_SITE
        return response
    
    if any(word in query_lower for word in ['курс', 'программ', 'обучен', 'занят']):
        program_info = find_relevant_sections("программ", knowledge_data)
        if program_info:
            response = "🎵 *Программы обучения*\n\n"
            for info in program_info:
                response += f"🎯 *{info['title']}*\n{info['content']}\n\n"
            response += f"🔗 Подробнее: {program_info[0]['url']}"
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
        f"- [Программы обучения]({PAGES['production']})\n"
        f"- [Частые вопросы]({PAGES['faq']})"
    )

# ================== ОБРАБОТЧИКИ TELEGRAM ================== #
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    """Приветственное сообщение о гитарной школе"""
    welcome_msg = (
        "🎵 *Добро пожаловать в SoundMusic54!*\n\n"
        "Я ваш персональный помощник гитарной школы. Чем могу помочь?\n\n"
        "🔹 Узнать стоимость обучения: спросите 'цены' или 'стоимость'\n"
        "🔹 Посмотреть программы: спросите 'программы обучения'\n"
        "🔹 Записаться на занятие: спросите 'как записаться?'\n\n"
        "Или просто задайте вопрос о школе, гитаре или обучении!\n\n"
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

if __name__ == '__main__':
    initialize_bot()
    
    # Запуск Flask в отдельном потоке
    flask_thread = threading.Thread(
        target=lambda: app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False),
        daemon=True
    )
    flask_thread.start()
    
    # Запуск бота
    logger.info("🤖 Запуск Telegram бота...")
    bot.infinity_polling()
