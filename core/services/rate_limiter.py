# core/services/rate_limiter.py
"""
Rate Limiter для защиты от блокировок Telegram/YouTube.

Использует алгоритм Token Bucket + Exponential Backoff.

Особенности:
- ✅ Token Bucket для каждого домена (t.me, youtube.com)
- ✅ Глобальный лимит запросов в минуту
- ✅ Exponential backoff с jitter при ошибках
- ✅ Приоритезация источников
- ✅ Статистика и логирование

Пример использования:
    rate_limiter = RateLimiter()
    
    # Перед запросом к Telegram
    await rate_limiter.acquire("telegram")
    
    # Перед запросом к YouTube
    await rate_limiter.acquire("youtube")
    
    # При ошибке
    await rate_limiter.record_error("telegram")
    
    # При успехе
    await rate_limiter.record_success("telegram")
"""

import asyncio
import logging
import time
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional

from core.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class TokenBucket:
    """
    Token Bucket алгоритм.
    
    Принцип работы:
    - Ведро ёмкостью `capacity` токенов
    - Токены добавляются со скоростью `refill_rate` в секунду
    - Каждый запрос потребляет 1 токен
    - Если токенов нет — ждём
    """
    capacity: int  # Максимум токенов
    refill_rate: float  # Токенов в секунду
    tokens: float = field(default=0.0, init=False)
    last_refill: float = field(default_factory=time.monotonic, init=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False, repr=False)
    
    def __post_init__(self):
        self.tokens = float(self.capacity)
    
    async def acquire(self, tokens: int = 1) -> float:
        """
        Запросить токены.
        
        Returns:
            Время ожидания в секундах (0 если токены доступны сразу)
        """
        async with self._lock:
            self._refill()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return 0.0
            
            # Вычисляем сколько ждать
            tokens_needed = tokens - self.tokens
            wait_time = tokens_needed / self.refill_rate
            
            logger.debug(f"⏳ Token bucket: ждём {wait_time:.2f}с (нужно {tokens_needed:.1f} токенов)")
            return wait_time
    
    def _refill(self):
        """Добавить токены в ведро"""
        now = time.monotonic()
        elapsed = now - self.last_refill
        tokens_to_add = elapsed * self.refill_rate
        
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now
    
    def __repr__(self) -> str:
        return f"TokenBucket(tokens={self.tokens:.1f}/{self.capacity})"


@dataclass
class ErrorBackoff:
    """
    Exponential Backoff для обработки ошибок.
    
    Формула: delay = min(base * (2 ^ errors), max_delay) + jitter
    
    Пример:
    - 1 ошибка: 1-2с
    - 2 ошибки: 2-4с
    - 3 ошибки: 4-8с
    - 4 ошибки: 8-16с
    - 5+ ошибок: 16-32с (максимум)
    """
    base_delay: float = 1.0  # Базовая задержка (сек)
    max_delay: float = 60.0  # Максимальная задержка (сек)
    jitter_factor: float = 0.1  # Фактор случайности (10%)
    
    _error_counts: Dict[str, int] = field(default_factory=dict, init=False, repr=False)
    _last_error: Dict[str, float] = field(default_factory=dict, init=False, repr=False)
    
    def record_error(self, key: str) -> float:
        """
        Записать ошибку и вернуть задержку.
        
        Returns:
            Задержка в секундах до следующей попытки
        """
        self._error_counts[key] = self._error_counts.get(key, 0) + 1
        self._last_error[key] = time.monotonic()
        
        errors = self._error_counts[key]
        delay = min(self.base_delay * (2 ** (errors - 1)), self.max_delay)
        
        # Добавляем jitter (случайность)
        jitter = delay * self.jitter_factor * random.uniform(-1, 1)
        delay += jitter
        
        logger.warning(f"⚠️ Error backoff для {key}: {errors} ошибок, задержка {delay:.1f}с")
        return delay
    
    def record_success(self, key: str):
        """Сбросить счётчик ошибок при успехе"""
        if key in self._error_counts:
            errors = self._error_counts[key]
            if errors > 0:
                logger.info(f"✅ Сброс error backoff для {key} (было {errors} ошибок)")
            del self._error_counts[key]
    
    def get_error_count(self, key: str) -> int:
        """Получить текущее число ошибок"""
        return self._error_counts.get(key, 0)
    
    def reset(self):
        """Сбросить все счётчики"""
        self._error_counts.clear()
        self._last_error.clear()


@dataclass
class RateLimitStats:
    """Статистика rate limiting"""
    total_requests: int = 0
    total_waits: int = 0
    total_wait_time: float = 0.0
    total_errors: int = 0
    last_request: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        return {
            "total_requests": self.total_requests,
            "total_waits": self.total_waits,
            "avg_wait_time": self.total_wait_time / max(1, self.total_waits),
            "error_rate": self.total_errors / max(1, self.total_requests),
        }


class RateLimiter:
    """
    Центральный rate limiter для проекта.
    
    Конфигурация по умолчанию (из settings.py):
    - Telegram: 10 запросов/сек (ведро 20 токенов)
    - YouTube: 1 запрос/сек (ведро 5 токенов)
    - Глобально: 60 запросов/мин
    """
    
    def __init__(
        self,
        telegram_capacity: Optional[int] = None,
        telegram_refill_rate: Optional[float] = None,
        youtube_capacity: Optional[int] = None,
        youtube_refill_rate: Optional[float] = None,
        global_requests_per_minute: Optional[int] = None,
    ):
        # Используем настройки из settings.py по умолчанию
        tg_capacity = telegram_capacity or settings.RATE_LIMIT_TELEGRAM_TOKENS
        tg_refill = telegram_refill_rate or settings.RATE_LIMIT_TELEGRAM_REFILL
        yt_capacity = youtube_capacity or settings.RATE_LIMIT_YOUTUBE_TOKENS
        yt_refill = youtube_refill_rate or settings.RATE_LIMIT_YOUTUBE_REFILL
        global_limit = global_requests_per_minute or settings.RATE_LIMIT_GLOBAL_PER_MINUTE
        
        # Token buckets для каждого домена
        self._buckets: Dict[str, TokenBucket] = {
            "telegram": TokenBucket(capacity=tg_capacity, refill_rate=tg_refill),
            "youtube": TokenBucket(capacity=yt_capacity, refill_rate=yt_refill),
        }
        
        # Error backoff
        self._backoff = ErrorBackoff(base_delay=1.0, max_delay=60.0)
        
        # Глобальный лимит (запросов в минуту)
        self._global_limit = global_limit
        self._global_requests: list[float] = []
        self._global_lock = asyncio.Lock()
        
        # Статистика
        self._stats: Dict[str, RateLimitStats] = {
            "telegram": RateLimitStats(),
            "youtube": RateLimitStats(),
            "global": RateLimitStats(),
        }
        
        logger.info(
            f"🚀 RateLimiter инициализирован: "
            f"Telegram={tg_capacity} токенов/{tg_refill}ток/с, "
            f"YouTube={yt_capacity} токенов/{yt_refill}ток/с, "
            f"Глобально={global_limit} запросов/мин"
        )
    
    async def acquire(self, domain: str, tokens: int = 1) -> float:
        """
        Запросить разрешение на запрос к домену.

        Args:
            domain: "telegram" или "youtube"
            tokens: Количество токенов (обычно 1)

        Returns:
            Время ожидания в секундах

        Example:
            wait_time = await rate_limiter.acquire("telegram")
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            # Делаем запрос к Telegram
        """
        if domain not in self._buckets:
            raise ValueError(f"Неизвестный домен: {domain}. Доступны: {list(self._buckets.keys())}")

        bucket = self._buckets[domain]

        # 1. СНАЧАЛА проверяем глобальный лимит (чтобы не ждать токены зря)
        global_wait = await self._check_global_limit()

        # 2. Потом ждём токены из bucket
        bucket_wait = await bucket.acquire(tokens)

        # 3. Берём максимальное время ожидания
        wait_time = max(global_wait, bucket_wait)
        
        # Обновляем статистику
        await self._update_stats(domain, waited=wait_time > 0, wait_time=wait_time)
        
        if wait_time > 0:
            logger.debug(f"⏳ Rate limit для {domain}: ждём {wait_time:.2f}с")
        
        return wait_time
    
    async def _check_global_limit(self) -> float:
        """Проверить глобальный лимит запросов в минуту"""
        async with self._global_lock:
            now = time.monotonic()
            
            # Удаляем запросы старше 60 секунд
            self._global_requests = [t for t in self._global_requests if now - t < 60]
            
            if len(self._global_requests) >= self._global_limit:
                # Ждём пока освободится слот
                oldest = self._global_requests[0]
                wait_time = 60 - (now - oldest)
                return max(0, wait_time)
            
            # Добавляем текущий запрос
            self._global_requests.append(now)
            return 0.0
    
    async def _update_stats(self, domain: str, waited: bool, wait_time: float):
        """Обновить статистику"""
        stats = self._stats.get(domain)
        if stats:
            stats.total_requests += 1
            if waited:
                stats.total_waits += 1
                stats.total_wait_time += wait_time
            stats.last_request = datetime.now(timezone.utc).replace(tzinfo=None)
    
    def record_error(self, domain: str, source_key: Optional[str] = None):
        """
        Записать ошибку запроса.

        Args:
            domain: "telegram" или "youtube"
            source_key: Уникальный ключ источника (например, username)
        """
        key = f"{domain}:{source_key}" if source_key else domain
        delay = self._backoff.record_error(key)

        stats = self._stats.get(domain)
        if stats:
            stats.total_errors += 1

        logger.warning(f"❌ Ошибка {domain} ({key}): backoff {delay:.1f}с")

    def record_success(self, domain: str, source_key: Optional[str] = None):
        """
        Записать успешный запрос.

        Args:
            domain: "telegram" или "youtube"
            source_key: Уникальный ключ источника
        """
        key = f"{domain}:{source_key}" if source_key else domain
        self._backoff.record_success(key)
        logger.debug(f"✅ Успех {domain} ({key})")

    def get_backoff_delay(self, domain: str, source_key: str) -> float:
        """
        Получить текущую задержку backoff для источника.

        Returns:
            Задержка в секундах (0 если ошибок не было)
        """
        key = f"{domain}:{source_key}"
        errors = self._backoff.get_error_count(key)

        if errors == 0:
            return 0.0

        delay = min(1.0 * (2 ** (errors - 1)), 60.0)
        jitter = delay * 0.1 * random.uniform(-1, 1)
        return delay + jitter

    def should_skip_source(self, domain: str, source_key: str) -> bool:
        """
        Проверить, нужно ли пропустить источник из-за частых ошибок.

        Returns:
            True если источник нужно пропустить
        """
        errors = self._backoff.get_error_count(f"{domain}:{source_key}")
        return errors >= 5  # Пропускаем после 5 ошибок подряд
    
    def get_stats(self) -> dict:
        """Получить статистику rate limiting"""
        return {
            domain: stats.to_dict()
            for domain, stats in self._stats.items()
        }
    
    def get_bucket_status(self) -> dict:
        """Получить статус token buckets"""
        return {
            domain: {
                "tokens": bucket.tokens,
                "capacity": bucket.capacity,
                "refill_rate": bucket.refill_rate,
            }
            for domain, bucket in self._buckets.items()
        }
    
    async def reset(self):
        """Сбросить все лимиты и статистику"""
        for bucket in self._buckets.values():
            bucket.tokens = bucket.capacity
            bucket.last_refill = time.monotonic()
        
        self._backoff.reset()
        
        async with self._global_lock:
            self._global_requests.clear()
        
        logger.info("🔄 RateLimiter сброшен")


# Глобальный экземпляр (singleton)
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Получить глобальный rate limiter"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def reset_rate_limiter():
    """Сбросить глобальный rate limiter (для тестов)"""
    global _rate_limiter
    _rate_limiter = None
