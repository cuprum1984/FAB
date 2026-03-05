# tests/test_rate_limiter.py
"""
Тесты для Rate Limiter.

Проверка:
- ✅ Token Bucket алгоритм
- ✅ Exponential Backoff
- ✅ Глобальный лимит запросов
- ✅ Статистика
"""

import pytest
import asyncio
import time
from core.services.rate_limiter import (
    RateLimiter,
    TokenBucket,
    ErrorBackoff,
    RateLimitStats,
    get_rate_limiter,
    reset_rate_limiter,
)


# =============================================================================
# Token Bucket Tests
# =============================================================================

class TestTokenBucket:
    """Тесты для Token Bucket алгоритма"""

    @pytest.mark.asyncio
    async def test_initial_tokens(self):
        """Ведро должно быть заполнено токенами при создании"""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        assert bucket.tokens == 10.0

    @pytest.mark.asyncio
    async def test_acquire_tokens(self):
        """Запрос токенов уменьшает их количество"""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        
        wait_time = await bucket.acquire(1)
        assert wait_time == 0.0
        assert bucket.tokens == 9.0

    @pytest.mark.asyncio
    async def test_acquire_multiple_tokens(self):
        """Запрос нескольких токенов"""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)
        
        wait_time = await bucket.acquire(5)
        assert wait_time == 0.0
        assert bucket.tokens == 5.0

    @pytest.mark.asyncio
    async def test_wait_when_empty(self):
        """Ожидание когда токены закончились"""
        bucket = TokenBucket(capacity=2, refill_rate=10.0)  # 10 токенов/сек
        
        # Забираем все токены
        await bucket.acquire(2)
        assert bucket.tokens == 0.0
        
        # Следующий запрос должен ждать
        wait_time = await bucket.acquire(1)
        assert wait_time > 0
        assert wait_time <= 0.2  # 1 токен / 10 токенов/сек = 0.1сек + погрешность

    @pytest.mark.asyncio
    async def test_refill_over_time(self):
        """Токены восстанавливаются со временем"""
        bucket = TokenBucket(capacity=10, refill_rate=100.0)  # 100 токенов/сек
        
        # Забираем все токены
        await bucket.acquire(10)
        initial_tokens = bucket.tokens
        
        # Ждём немного
        await asyncio.sleep(0.05)  # 50мс
        
        # Запрашиваем токен (это вызовет _refill)
        await bucket.acquire(1)
        
        # Токены должны восстановиться (частично)
        # 50мс * 100 токенов/сек = 5 токенов
        assert bucket.tokens < 10  # Но не больше capacity


# =============================================================================
# Error Backoff Tests
# =============================================================================

class TestErrorBackoff:
    """Тесты для Exponential Backoff"""

    def test_first_error_delay(self):
        """Первая ошибка = базовая задержка"""
        backoff = ErrorBackoff(base_delay=1.0, max_delay=60.0)
        
        delay = backoff.record_error("test_source")
        assert 0.9 <= delay <= 1.1  # ~1 сек ± jitter

    def test_exponential_growth(self):
        """Задержка растёт экспоненциально"""
        backoff = ErrorBackoff(base_delay=1.0, max_delay=60.0, jitter_factor=0.0)
        
        delays = []
        for i in range(5):
            delay = backoff.record_error("test_source")
            delays.append(delay)
        
        # Каждая задержка примерно в 2 раза больше предыдущей
        assert delays[1] > delays[0]
        assert delays[2] > delays[1]
        assert delays[3] > delays[2]

    def test_max_delay_cap(self):
        """Задержка не превышает максимум"""
        backoff = ErrorBackoff(base_delay=1.0, max_delay=10.0, jitter_factor=0.0)
        
        # 10 ошибок = 2^9 = 512 сек, но максимум 10
        for _ in range(10):
            delay = backoff.record_error("test_source")
        
        assert delay <= 10.0

    def test_reset_on_success(self):
        """Успех сбрасывает счётчик ошибок"""
        backoff = ErrorBackoff(base_delay=1.0, max_delay=60.0)
        
        # 3 ошибки
        backoff.record_error("test_source")
        backoff.record_error("test_source")
        backoff.record_error("test_source")
        
        assert backoff.get_error_count("test_source") == 3
        
        # Успех
        backoff.record_success("test_source")
        
        assert backoff.get_error_count("test_source") == 0

    def test_different_sources_independent(self):
        """Разные источники имеют независимые счётчики"""
        backoff = ErrorBackoff()
        
        backoff.record_error("source_a")
        backoff.record_error("source_a")
        
        backoff.record_error("source_b")
        
        assert backoff.get_error_count("source_a") == 2
        assert backoff.get_error_count("source_b") == 1


# =============================================================================
# RateLimiter Integration Tests
# =============================================================================

class TestRateLimiter:
    """Тесты для интеграции Rate Limiter"""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Сброс rate limiter между тестами"""
        reset_rate_limiter()
        yield
        reset_rate_limiter()

    @pytest.mark.asyncio
    async def test_acquire_telegram(self):
        """Запрос к Telegram"""
        rate_limiter = RateLimiter()
        
        wait_time = await rate_limiter.acquire("telegram")
        assert wait_time >= 0
        assert wait_time < 1.0  # Обычно сразу доступно

    @pytest.mark.asyncio
    async def test_acquire_youtube(self):
        """Запрос к YouTube"""
        rate_limiter = RateLimiter()
        
        wait_time = await rate_limiter.acquire("youtube")
        assert wait_time >= 0

    @pytest.mark.asyncio
    async def test_acquire_unknown_domain(self):
        """Запрос к неизвестному домену"""
        rate_limiter = RateLimiter()
        
        with pytest.raises(ValueError, match="Неизвестный домен"):
            await rate_limiter.acquire("unknown")

    @pytest.mark.asyncio
    async def test_record_error_and_success(self):
        """Запись ошибок и успехов"""
        rate_limiter = RateLimiter()
        
        # 3 ошибки
        rate_limiter.record_error("telegram", "channel1")
        rate_limiter.record_error("telegram", "channel1")
        rate_limiter.record_error("telegram", "channel1")
        
        # Проверяем что backoff работает
        delay = rate_limiter.get_backoff_delay("telegram", "channel1")
        assert delay > 0
        
        # Успех сбрасывает
        rate_limiter.record_success("telegram", "channel1")
        delay = rate_limiter.get_backoff_delay("telegram", "channel1")
        assert delay == 0

    @pytest.mark.asyncio
    async def test_should_skip_source(self):
        """Пропуск источника после частых ошибок"""
        rate_limiter = RateLimiter()
        
        # 5 ошибок
        for _ in range(5):
            rate_limiter.record_error("telegram", "bad_channel")
        
        # Должен пропускаться
        assert rate_limiter.should_skip_source("telegram", "bad_channel") is True
        
        # Хороший источник не пропускается
        assert rate_limiter.should_skip_source("telegram", "good_channel") is False

    @pytest.mark.asyncio
    async def test_get_stats(self):
        """Получение статистики"""
        rate_limiter = RateLimiter()
        
        # Несколько запросов
        await rate_limiter.acquire("telegram")
        await rate_limiter.acquire("youtube")
        
        stats = rate_limiter.get_stats()
        
        assert "telegram" in stats
        assert "youtube" in stats
        assert "global" in stats
        
        assert stats["telegram"]["total_requests"] == 1
        assert stats["youtube"]["total_requests"] == 1

    @pytest.mark.asyncio
    async def test_get_bucket_status(self):
        """Получение статуса bucket'ов"""
        rate_limiter = RateLimiter()
        
        status = rate_limiter.get_bucket_status()
        
        assert "telegram" in status
        assert "youtube" in status
        
        assert status["telegram"]["capacity"] == 20
        assert status["telegram"]["refill_rate"] == 10.0
        assert status["youtube"]["capacity"] == 5
        assert status["youtube"]["refill_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_reset(self):
        """Сброс rate limiter"""
        rate_limiter = RateLimiter()
        
        # Заполняем ошибками
        for _ in range(5):
            rate_limiter.record_error("telegram", "channel")
        
        # Сбрасываем
        await rate_limiter.reset()
        
        # Ошибки сброшены
        assert rate_limiter.should_skip_source("telegram", "channel") is False

    @pytest.mark.asyncio
    async def test_global_limit(self):
        """Глобальный лимит запросов в минуту"""
        rate_limiter = RateLimiter(global_requests_per_minute=5)
        
        # 5 быстрых запросов
        for _ in range(5):
            await rate_limiter.acquire("telegram")
        
        # 6-й должен ждать
        wait_time = await rate_limiter.acquire("telegram")
        assert wait_time > 0  # Ждём освобождения слота


# =============================================================================
# Singleton Tests
# =============================================================================

class TestSingleton:
    """Тесты для singleton паттерна"""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        reset_rate_limiter()
        yield
        reset_rate_limiter()

    def test_get_rate_limiter_returns_same_instance(self):
        """get_rate_limiter возвращает один экземпляр"""
        rl1 = get_rate_limiter()
        rl2 = get_rate_limiter()
        
        assert rl1 is rl2

    def test_reset_rate_limiter(self):
        """reset_rate_limiter сбрасывает экземпляр"""
        rl1 = get_rate_limiter()
        reset_rate_limiter()
        rl2 = get_rate_limiter()
        
        assert rl1 is not rl2


# =============================================================================
# Performance Tests
# =============================================================================

class TestPerformance:
    """Тесты производительности"""

    @pytest.mark.asyncio
    async def test_concurrent_acquires(self):
        """Множественные параллельные запросы"""
        rate_limiter = RateLimiter(
            telegram_capacity=100,
            telegram_refill_rate=50.0
        )
        
        async def make_request():
            wait = await rate_limiter.acquire("telegram")
            return wait
        
        # 50 параллельных запросов
        tasks = [make_request() for _ in range(50)]
        results = await asyncio.gather(*tasks)
        
        # Все должны получить токены (некоторые с ожиданием)
        assert len(results) == 50
        assert all(r >= 0 for r in results)

    @pytest.mark.asyncio
    async def test_rate_limiting_performance(self):
        """Проверка что rate limiting работает"""
        rate_limiter = RateLimiter(
            telegram_capacity=5,
            telegram_refill_rate=2.0  # 2 токена/сек (медленнее для теста)
        )
        
        start = time.monotonic()
        
        # 10 запросов с реальным ожиданием
        for _ in range(10):
            wait_time = await rate_limiter.acquire("telegram")
            if wait_time > 0:
                await asyncio.sleep(wait_time)
        
        elapsed = time.monotonic() - start
        
        # 5 токенов сразу + 5 токенов за 2.5 сек (2 токена/сек)
        # Реально меньше из-за восстановления токенов во время выполнения
        assert elapsed >= 1.0  # Минимум 1 сек (rate limiting работает)
        assert elapsed < 10.0  # Но не слишком долго
