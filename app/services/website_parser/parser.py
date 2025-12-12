# app/services/website_parser/parser.py

"""
Парсер веб-сайтов для извлечения текстового контента.
Очищает HTML от мусора и извлекает основной контент.
"""

import re
import asyncio
from typing import Optional, Tuple
from urllib.parse import urlparse, urljoin

import aiohttp
from bs4 import BeautifulSoup
from app.core.logging import get_logger

logger = get_logger(__name__)


# Элементы, которые нужно удалить (реклама, навигация, футеры и т.д.)
REMOVE_SELECTORS = [
    'script', 'style', 'nav', 'header', 'footer', 'aside',
    '[class*="ad"]', '[class*="advertisement"]', '[class*="banner"]',
    '[class*="cookie"]', '[class*="popup"]', '[class*="modal"]',
    '[id*="ad"]', '[id*="advertisement"]', '[id*="banner"]',
    '[class*="menu"]', '[class*="navigation"]', '[class*="sidebar"]',
    '[class*="comment"]', '[class*="social"]', '[class*="share"]',
]


def clean_html_text(html: str) -> str:
    """
    Очищает HTML от мусора и извлекает чистый текст.
    
    Args:
        html: HTML содержимое страницы
    
    Returns:
        Очищенный текст
    """
    if not html:
        return ""
    
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        # Удаляем ненужные элементы
        for selector in REMOVE_SELECTORS:
            for element in soup.select(selector):
                element.decompose()
        
        # Удаляем пустые элементы
        for element in soup.find_all(['div', 'span', 'p']):
            if not element.get_text(strip=True):
                element.decompose()
        
        # Извлекаем текст из основных контентных элементов
        # Приоритет: article > main > [role="main"] > body
        content = None
        
        for selector in ['article', 'main', '[role="main"]', 'body']:
            elements = soup.select(selector)
            if elements:
                content = elements[0]
                break
        
        if not content:
            content = soup
        
        # Извлекаем текст
        text = content.get_text(separator=' ', strip=True)
        
        # Очищаем от лишних пробелов и переносов
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n', text)
        
        return text.strip()
        
    except Exception as e:
        logger.error(f"Ошибка при очистке HTML: {e}")
        return ""


def extract_main_content(text: str, max_length: int = 10000) -> str:
    """
    Извлекает основной контент из текста, уменьшая количество токенов.
    Удаляет повторяющиеся фразы, короткие предложения и мусор.
    
    Args:
        text: Исходный текст
        max_length: Максимальная длина текста
    
    Returns:
        Очищенный и сокращенный текст
    """
    if not text:
        return ""
    
    # Разбиваем на предложения
    sentences = re.split(r'[.!?]\s+', text)
    
    # Фильтруем предложения
    filtered_sentences = []
    seen_phrases = set()
    
    for sentence in sentences:
        sentence = sentence.strip()
        
        # Пропускаем слишком короткие предложения
        if len(sentence) < 20:
            continue
        
        # Пропускаем предложения только из цифр и символов
        if re.match(r'^[\d\s\W]+$', sentence):
            continue
        
        # Пропускаем повторяющиеся фразы (первые 30 символов)
        phrase_key = sentence[:30].lower()
        if phrase_key in seen_phrases:
            continue
        seen_phrases.add(phrase_key)
        
        filtered_sentences.append(sentence)
    
    # Объединяем предложения
    result = '. '.join(filtered_sentences)
    
    # Ограничиваем длину
    if len(result) > max_length:
        result = result[:max_length] + "..."
    
    return result


async def parse_website(url: str, timeout: int = 10) -> Tuple[Optional[str], Optional[str]]:
    """
    Парсит веб-сайт и извлекает очищенный текст.
    
    Args:
        url: URL сайта
        timeout: Таймаут запроса в секундах
    
    Returns:
        Кортеж (текст, ошибка). Если ошибка - текст None.
    """
    # Нормализуем URL
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    try:
        # Проверяем валидность URL
        parsed = urlparse(url)
        if not parsed.netloc:
            logger.warning(f"[PARSER] Некорректный URL: {url}")
            return None, "Некорректный URL"
        
        logger.info(f"[PARSER] Начинаю загрузку страницы: {url}")
        
        # Загружаем страницу
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=timeout),
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        ) as session:
            async with session.get(url, allow_redirects=True) as response:
                logger.info(f"[PARSER] HTTP статус: {response.status}, Content-Type: {response.headers.get('Content-Type', 'unknown')}")
                
                if response.status != 200:
                    logger.error(f"[PARSER] Ошибка HTTP {response.status} для {url}")
                    return None, f"Ошибка HTTP {response.status}"
                
                # Проверяем Content-Type
                content_type = response.headers.get('Content-Type', '')
                if 'text/html' not in content_type:
                    logger.warning(f"[PARSER] Не HTML контент: {content_type} для {url}")
                    return None, f"Не HTML контент: {content_type}"
                
                html = await response.text()
                logger.info(f"[PARSER] Загружено HTML: {len(html)} символов")
        
        # Очищаем HTML и извлекаем текст
        logger.info(f"[PARSER] Начинаю очистку HTML...")
        text = clean_html_text(html)
        
        if not text or len(text) < 50:
            logger.warning(f"[PARSER] Не удалось извлечь достаточное количество текста: {len(text) if text else 0} символов")
            return None, "Не удалось извлечь достаточное количество текста"
        
        # Уменьшаем количество токенов
        original_length = len(text)
        text = extract_main_content(text, max_length=8000)
        final_length = len(text)
        
        logger.info(
            f"[PARSER] Парсинг сайта {url}: "
            f"извлечено {original_length} символов, "
            f"после очистки {final_length} символов "
            f"(сокращение: {((original_length - final_length) / original_length * 100) if original_length > 0 else 0:.1f}%)"
        )
        
        return text, None
        
    except asyncio.TimeoutError:
        return None, "Таймаут при загрузке страницы"
    except aiohttp.ClientError as e:
        return None, f"Ошибка сети: {e}"
    except Exception as e:
        logger.error(f"Ошибка при парсинге сайта {url}: {e}")
        return None, f"Ошибка: {e}"
