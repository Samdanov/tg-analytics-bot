"""
Proxy Channel Detector

Доменный сервис для определения каналов-прокладок.
Содержит бизнес-правила без привязки к инфраструктуре.
"""

import re
from dataclasses import dataclass
from typing import List, Tuple
from collections import Counter


# Константы для определения прокладки (Domain Rules)
# Вынесены в явные константы вместо магических чисел
MIN_LINKED_CHANNELS = 3
MAX_AVG_TEXT_PER_POST = 100  # символов
MIN_LINK_POSTS_RATIO = 0.5  # 50% постов содержат ссылки


@dataclass
class ProxyDetectionResult:
    """
    Результат проверки канала на прокладку.
    """
    is_proxy: bool
    linked_channels: List[Tuple[str, int]]  # [(username, mention_count), ...]
    avg_text_length: float
    link_posts_ratio: float
    total_posts: int
    
    @property
    def reason(self) -> str:
        """Человекочитаемая причина определения как прокладки."""
        if not self.is_proxy:
            return "Канал не является прокладкой"
        
        reasons = []
        reasons.append(f"Найдено {len(self.linked_channels)} упоминаемых каналов (>= {MIN_LINKED_CHANNELS})")
        reasons.append(f"Средняя длина текста: {self.avg_text_length:.0f} символов (< {MAX_AVG_TEXT_PER_POST})")
        reasons.append(f"Доля постов со ссылками: {self.link_posts_ratio:.1%} (> {MIN_LINK_POSTS_RATIO:.0%})")
        
        return " | ".join(reasons)


class ProxyChannelDetector:
    """
    Сервис для определения каналов-прокладок.
    
    Канал-прокладка: канал, основная цель которого - делиться ссылками на другие каналы,
    а не создавать собственный контент.
    
    Критерии прокладки:
    1. Упоминает >= 3 уникальных каналов
    2. Средняя длина текста (без ссылок) < 100 символов
    3. Более 50% постов содержат ссылки на каналы
    """
    
    # Регулярные выражения для поиска упоминаний каналов
    CHANNEL_LINK_RE = re.compile(r"(?:https?://)?(?:www\.)?t\.me/([A-Za-z0-9_]{3,})")
    USERNAME_MENTION_RE = re.compile(r"@([A-Za-z0-9_]{3,})")
    
    # Служебные ссылки, которые нужно игнорировать
    IGNORE_PATTERNS = {"joinchat", "c/", "+"}
    
    def __init__(
        self,
        min_linked_channels: int = MIN_LINKED_CHANNELS,
        max_avg_text: int = MAX_AVG_TEXT_PER_POST,
        min_link_ratio: float = MIN_LINK_POSTS_RATIO
    ):
        """
        Args:
            min_linked_channels: Минимальное количество уникальных упоминаемых каналов
            max_avg_text: Максимальная средняя длина текста (без ссылок)
            min_link_ratio: Минимальная доля постов со ссылками
        """
        self.min_linked_channels = min_linked_channels
        self.max_avg_text = max_avg_text
        self.min_link_ratio = min_link_ratio
    
    def detect(
        self,
        posts: List[dict],
        exclude_username: str = None
    ) -> ProxyDetectionResult:
        """
        Определяет, является ли канал прокладкой на основе его постов.
        
        Args:
            posts: Список постов канала (dict с полем 'text')
            exclude_username: Username текущего канала (исключить из подсчета)
        
        Returns:
            ProxyDetectionResult
        """
        if not posts:
            return ProxyDetectionResult(
                is_proxy=False,
                linked_channels=[],
                avg_text_length=0.0,
                link_posts_ratio=0.0,
                total_posts=0
            )
        
        linked_channels = self._extract_linked_channels(posts, exclude_username)
        avg_text_length = self._calculate_avg_text_length(posts)
        link_posts_ratio = self._calculate_link_posts_ratio(posts)
        
        # Применяем бизнес-правила
        is_proxy = (
            len(linked_channels) >= self.min_linked_channels
            and avg_text_length < self.max_avg_text
            and link_posts_ratio > self.min_link_ratio
        )
        
        return ProxyDetectionResult(
            is_proxy=is_proxy,
            linked_channels=linked_channels,
            avg_text_length=avg_text_length,
            link_posts_ratio=link_posts_ratio,
            total_posts=len(posts)
        )
    
    def _extract_linked_channels(
        self,
        posts: List[dict],
        exclude_username: str = None
    ) -> List[Tuple[str, int]]:
        """
        Извлекает все упоминания каналов из постов.
        
        Returns:
            Список (username, count) отсортированный по частоте
        """
        channels = []
        exclude_lower = exclude_username.lower() if exclude_username else None
        
        for post in posts:
            text = post.get("text", "") or ""
            
            # Ищем ссылки вида t.me/channel
            for match in self.CHANNEL_LINK_RE.finditer(text):
                username = match.group(1).lstrip("@").lower()
                
                # Фильтруем служебные и текущий канал
                if self._should_skip_username(username, exclude_lower):
                    continue
                
                channels.append(username)
            
            # Ищем упоминания вида @channel
            for match in self.USERNAME_MENTION_RE.finditer(text):
                username = match.group(1).lstrip("@").lower()
                
                if self._should_skip_username(username, exclude_lower):
                    continue
                
                channels.append(username)
        
        if not channels:
            return []
        
        # Подсчитываем частоту и возвращаем топ-10
        counter = Counter(channels)
        return counter.most_common(10)
    
    def _should_skip_username(self, username: str, exclude_username: str = None) -> bool:
        """Проверяет, нужно ли пропустить этот username."""
        if not username:
            return True
        
        # Проверка на служебные шаблоны
        for pattern in self.IGNORE_PATTERNS:
            if username.startswith(pattern):
                return True
        
        # Исключаем текущий канал
        if exclude_username and username == exclude_username:
            return True
        
        return False
    
    def _calculate_avg_text_length(self, posts: List[dict]) -> float:
        """
        Вычисляет среднюю длину текста в постах (без ссылок).
        """
        total_text_length = 0
        
        for post in posts:
            text = post.get("text", "") or ""
            
            # Удаляем все ссылки
            text_without_links = self.CHANNEL_LINK_RE.sub("", text)
            text_without_links = self.USERNAME_MENTION_RE.sub("", text_without_links)
            
            clean_text = text_without_links.strip()
            total_text_length += len(clean_text)
        
        return total_text_length / len(posts) if posts else 0.0
    
    def _calculate_link_posts_ratio(self, posts: List[dict]) -> float:
        """
        Вычисляет долю постов, содержащих ссылки на каналы.
        """
        posts_with_links = 0
        
        for post in posts:
            text = post.get("text", "") or ""
            
            has_links = (
                self.CHANNEL_LINK_RE.search(text) is not None
                or self.USERNAME_MENTION_RE.search(text) is not None
            )
            
            if has_links:
                posts_with_links += 1
        
        return posts_with_links / len(posts) if posts else 0.0

