# ... (предыдущий код остается без изменений до функций)

# --- УЛУЧШЕННАЯ ФУНКЦИЯ РАЗБИЕНИЯ СООБЩЕНИЙ ---
def split_message(text: str, limit=4096) -> list:
    """
    Надежно разбивает текст на части, гарантируя целостность слов и предложений.
    Возвращает список частей.
    """
    if len(text) <= limit:
        return [text]
    
    parts = []
    while text:
        # Если оставшийся текст меньше лимита - добавляем и выходим
        if len(text) <= limit:
            parts.append(text)
            break
            
        # Находим последний пробел/перенос строки в пределах лимита
        split_index = limit
        for i in range(limit, max(0, limit-50), -1):
            if text[i] in (' ', '\n', '.', ',', ';', '!', '?'):
                split_index = i + 1  # включаем разделитель
                break
                
        parts.append(text[:split_index].strip())
        text = text[split_index:].strip()
        
    return parts

# --- ДОБАВЛЕНА ОБРАБОТКА ДЛИННЫХ ОТВЕТОВ ---
@bot.message_handler(func=lambda m: True)
def handle_msg(m):
    q = m.text.strip()
    if not q:
        return bot.send_message(m.chat.id, "❓ Напиши, пожалуйста, текстом.")
    
    bot.send_chat_action(m.chat.id, "typing")
    
    try:
        # Получаем ответ от нейросети
        ans = ask_deepseek(q)
        # Экранируем спецсимволы Markdown
        safe_text = safe_markdown(ans)
        # Разбиваем на части
        chunks = split_message(safe_text)
        total_chunks = len(chunks)
        
        # Отправляем с прогрессом
        for i, chunk in enumerate(chunks):
            progress = f"({i+1}/{total_chunks}) " if total_chunks > 1 else ""
            full_chunk = progress + chunk
            
            try:
                bot.send_message(
                    m.chat.id, 
                    full_chunk, 
                    parse_mode="MarkdownV2",
                    disable_web_page_preview=True
                )
            except Exception as e:
                print(f"⚠️ Ошибка отправки: {e}")
                # Фолбэк: отправка без разметки
                bot.send_message(m.chat.id, full_chunk)
                
            # Небольшая задержка между частями
            time.sleep(0.3)
            
    except Exception as e:
        error_msg = f"⚠️ Ошибка: {str(e)[:200]}"
        bot.send_message(m.chat.id, "Что-то пошло не так... Попробуйте задать вопрос иначе")
        print(f"❌ Ошибка обработки сообщения: {e}")

# ... (остальной код без изменений)
