#!/usr/bin/env python3
"""
TUI интерфейс для чата с ИИ на базе curses
"""

import curses
import textwrap
import threading
import locale
import json

from anthropic.types import MessageParam

import config


class ChatTUI:
    def __init__(self, client, model, max_tokens, temperature, system_prompt):
        self.client = client
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.system_prompt = system_prompt
        self.conversation = []
        self.messages = []
        self.current_input = ""
        self.scroll_offset = 0
        self.waiting_for_response = False

    def wrap_text(self, text, width):
        """Переносит текст по словам, сохраняя переносы строк"""
        lines = text.split('\n')
        wrapped_lines = []
        for line in lines:
            if line.strip():  # Не пустая строка
                wrapped_lines.extend(textwrap.wrap(line, width=width))
            else:  # Пустая строка
                wrapped_lines.append('')
        return wrapped_lines
        
    def add_message(self, role, content):
        """Добавляет сообщение в чат"""
        self.messages.append({"role": role, "content": content})
        self.conversation.append(MessageParam(role=role, content=content))
        
    def get_ai_response(self, stdscr):
        """Получает ответ от ИИ в отдельном потоке"""
        self.waiting_for_response = True
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=self.system_prompt,
                messages=self.conversation,
            )
            response = message.content[0].text
            self.add_message("assistant", response)
        except Exception as e:
            self.add_message("system", f"Ошибка: {str(e)}")
        finally:
            self.waiting_for_response = False
            
    def draw_chat(self, stdscr, chat_height, width):
        """Рисует область чата"""
        # Очищаем область чата
        for i in range(chat_height):
            stdscr.addstr(i, 0, "" * (width - 1))
            
        # Отображаем сообщения
        y = 0
        visible_messages = self.messages[self.scroll_offset:]
        
        for msg in visible_messages:
            if y >= chat_height - 1:
                break
                
            role_prefix = "Вы: " if msg["role"] == "user" else ("ИИ: " if msg["role"] == "assistant" else "Система: ")
            wrapped_lines = self.wrap_text(msg["content"], width - len(role_prefix) - 2)
            
            # Первая строка с префиксом
            if wrapped_lines:
                try:
                    stdscr.addstr(y, 0, role_prefix + wrapped_lines[0][:width-1])
                    y += 1
                    
                    # Остальные строки с отступом
                    for line in wrapped_lines[1:]:
                        if y >= chat_height - 1:
                            break
                        stdscr.addstr(y, len(role_prefix), line[:width-len(role_prefix)-1])
                        y += 1
                except curses.error:
                    pass
                    
        # Показываем индикатор загрузки
        if self.waiting_for_response:
            try:
                stdscr.addstr(y, 0, "ИИ печатает...")
            except curses.error:
                pass
                
    def draw_input(self, stdscr, y_pos, width):
        """Рисует область ввода"""
        # Горизонтальная линия-разделитель
        try:
            stdscr.addstr(y_pos, 0, "-" * (width - 1))
            stdscr.addstr(y_pos + 1, 0, "> " + self.current_input[:width-3])
            stdscr.addstr(y_pos + 2, 0, "Напечатай сообщение или нажми Ctrl-C для выхода", curses.color_pair(2))
        except curses.error:
            pass
            
    def run(self, stdscr):
        """Главный цикл TUI"""
        curses.curs_set(1)  # Показать курсор
        stdscr.timeout(100)  # Неблокирующий ввод
        curses.start_color()  # Инициализация цветов
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)  # Обычный текст
        curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLACK)  # Тёмно-серый
        
        # Настройка для UTF-8
        locale.setlocale(locale.LC_ALL, '')

        # Приветствие
        self.add_message("assistant", config.GREETING)

        while True:
            height, width = stdscr.getmaxyx()
            chat_height = height - 4  # Оставляем место для ввода
            
            stdscr.clear()
            
            # Рисуем интерфейс
            self.draw_chat(stdscr, chat_height, width)
            self.draw_input(stdscr, chat_height, width)
            
            # Позиционируем курсор
            cursor_x = min(len(self.current_input) + 2, width - 1)
            try:
                stdscr.move(chat_height + 1, cursor_x)
            except curses.error:
                pass
                
            stdscr.refresh()

            # Обработка ввода
            try:
                key = stdscr.get_wch()
            except curses.error:
                key = -1  # timeout
            
            if key == '\n' or key == '\r' or key == curses.KEY_ENTER:
                if self.current_input.strip() and not self.waiting_for_response:
                    # Добавляем сообщение пользователя
                    self.add_message("user", self.current_input.strip())
                    self.current_input = ""
                    
                    # Запускаем получение ответа в отдельном потоке
                    threading.Thread(target=self.get_ai_response, args=(stdscr,), daemon=True).start()
            elif key == curses.KEY_BACKSPACE or key == '\b' or key == '\x7f':
                if self.current_input:
                    self.current_input = self.current_input[:-1]
            elif key == curses.KEY_UP:
                if self.scroll_offset > 0:
                    self.scroll_offset -= 1
            elif key == curses.KEY_DOWN:
                if self.scroll_offset < len(self.messages) - 1:
                    self.scroll_offset += 1
            elif isinstance(key, str) and key.isprintable():
                # Обычные печатные символы (включая кириллицу)
                self.current_input += key
