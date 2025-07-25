import os
import threading
import time
import requests
from bs4 import BeautifulSoup
import telebot
import re
from flask import Flask
from telebot.apihelper import ApiTelegramException

# ... (остальной код без изменений до функций разбиения сообщений) ...

def split_message(text: str, limit=4096) -> list:
    """
    Надежно разбивает текст на части, сохраняя целостность предложений
    и слов. Гарантирует, что сообщения не будут обрываться.
    """
    # Если текст полностью помещается в одно сообщение
    if len(text) <= limit:
        return [text]
    
    # Разбиваем текст на предложения
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    parts = []
    current_part = ""
    
    for sentence in sentences:
        # Проверяем, поместится ли предложение в текущую часть
        if len(current_part) + len(sentence) + 1 <= limit:
            current_part += (sentence + " ")
        else:
            # Если текущая часть не пустая - сохраняем ее
            if current_part:
                parts.append(current_part.strip())
                current_part = ""
            
            # Если одно предложение длиннее лимита
            if len(sentence) > limit:
                # Разбиваем по словам
                words = sentence.split()
                for word in words:
                    if len(current_part) + len(word) + 1 > limit:
                        parts.append(current_part.strip())
                        current_part = ""
                    current_part += (word + " ")
            else:
                current_part = sentence + " "
    
    # Добавляем последнюю часть
    if current_part.strip():
        parts.append(current_part.strip())
    
    return parts

@bot.message_handler(func=lambda m: True)
def handle_msg(m):
    q = m.text.strip()
    if not q:
        return bot.send_message(m.chat.id, "❓ Напиши, пожалуйста, текстом.")
    
    bot.send_chat_action(m.chat.id, "typing")
    
    try:
        ans = ask_deepseek(q)
        safe_text = safe_markdown(ans)
        chunks = split_message(safe_text)
        total_chunks = len(chunks)
        
        # Отправляем с индикацией прогресса
        for i, chunk in enumerate(chunks):
            # Добавляем индикатор прогресса только если частей больше 1
            prefix = f"({i+1}/{total_chunks}) " if total_chunks > 1 else ""
            
            # Добавляем "продолжение следует" для всех частей кроме последней
            suffix = "\n\n↪️ продолжение следует..." if i < total_chunks - 1 else ""
            
            full_message = prefix + chunk + suffix
            
            try:
                bot.send_message(
                    m.chat.id, 
                    full_message, 
                    parse_mode="MarkdownV2",
                    disable_web_page_preview=True
                )
            except Exception as e:
                print(f"⚠️ Ошибка отправки: {e}")
                # Фолбэк: отправка без разметки
                bot.send_message(m.chat.id, full_message)
                
            # Пауза между сообщениями
            time.sleep(0.5)
            
    except Exception as e:
        error_msg = f"⚠️ Ошибка: {str(e)[:200]}"
        bot.send_message(m.chat.id, "Что-то пошло не так... Попробуйте задать вопрос иначе")
        print(f"❌ Ошибка обработки сообщения: {e}")

# ... (остальной код без изменений) ...
