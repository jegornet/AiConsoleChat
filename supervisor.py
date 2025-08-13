#!/usr/bin/env python3
"""
Агент-супервайзер для оценки качества рекомендаций турагента
"""

import re
from anthropic.types import MessageParam


class SupervisorAgent:
    def __init__(self, client, model, max_tokens, temperature, system_prompt):
        self.client = client
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.system_prompt = system_prompt

    def should_evaluate(self, message_content):
        """Проверяет, содержит ли сообщение секции для оценки"""
        return "---ЗАПРОС" in message_content and "---РЕКОМЕНДАЦИИ" in message_content

    def extract_sections(self, message_content):
        """Извлекает секции ЗАПРОС и РЕКОМЕНДАЦИИ из сообщения"""
        try:
            # Ищем секцию ЗАПРОС
            request_match = re.search(r'---ЗАПРОС\s*(.*?)(?=---РЕКОМЕНДАЦИИ|$)', message_content, re.DOTALL)
            request_section = request_match.group(1).strip() if request_match else ""
            
            # Ищем секцию РЕКОМЕНДАЦИИ
            recommendations_match = re.search(r'---РЕКОМЕНДАЦИИ\s*(.*?)$', message_content, re.DOTALL)
            recommendations_section = recommendations_match.group(1).strip() if recommendations_match else ""
            
            return request_section, recommendations_section
        except Exception:
            return "", ""

    def evaluate_recommendations(self, message_content):
        """Оценивает соответствие рекомендаций запросу"""
        if not self.should_evaluate(message_content):
            return None

        request_section, recommendations_section = self.extract_sections(message_content)
        
        if not request_section or not recommendations_section:
            return None

        # Формируем промпт для супервайзера
        evaluation_prompt = f"""
Проанализируй соответствие рекомендаций турагента запросу пользователя.

ЗАПРОС ПОЛЬЗОВАТЕЛЯ:
{request_section}

РЕКОМЕНДАЦИИ ТУРАГЕНТА:
{recommendations_section}

Оцени качество рекомендаций согласно критериям в системном промпте.
"""

        try:
            # Запрос к API для оценки
            message = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=self.system_prompt,
                messages=[MessageParam(role="user", content=evaluation_prompt)]
            )
            
            return message.content[0].text
        except Exception as e:
            return f"Ошибка оценки супервайзера: {str(e)}"

    def parse_evaluation_score(self, evaluation_text):
        """Извлекает числовую оценку из текста оценки"""
        if not evaluation_text:
            return None
            
        # Ищем паттерн "Общая оценка: X/10"
        score_match = re.search(r'Общая оценка:\s*(\d+)/10', evaluation_text)
        if score_match:
            return int(score_match.group(1))
        
        # Альтернативный поиск числовой оценки
        score_match = re.search(r'(\d+)/10', evaluation_text)
        if score_match:
            return int(score_match.group(1))
            
        return None