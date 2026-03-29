# core/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    BOT_TOKEN: str
    DATABASE_URL: str
    #API_ID: int  # ID из my.telegram.org
    #API_HASH: str  # Hash из my.telegram.org

    # ✅ ДОБАВЛЯЕМ ENV
    ENV: str = "development"  # по умолчанию development

    DEFAULT_PARSING_INTERVAL: int = 300
    USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    REQUEST_TIMEOUT: int = 10

    # ✅ RATE LIMITING настройки
    RATE_LIMIT_TELEGRAM_TOKENS: int = 20  # Ёмкость ведра Telegram
    RATE_LIMIT_TELEGRAM_REFILL: float = 10.0  # Токенов в секунду (Telegram)
    RATE_LIMIT_YOUTUBE_TOKENS: int = 5  # Ёмкость ведра YouTube
    RATE_LIMIT_YOUTUBE_REFILL: float = 1.0  # Токенов в секунду (YouTube)
    RATE_LIMIT_GLOBAL_PER_MINUTE: int = 60  # Глобальный лимит запросов в минуту

    # ✅ SEMAPHORE для ограничения параллелизма
    SEMAPHORE_LIMIT: int = 10  # Максимум одновременных запросов к источникам

    # ✅ ЗАЩИТА ОТ СПАМА ПОСЛЕ ПРОСТОЯ
    DOWNTIME_THRESHOLD_SECONDS: int = 600  # 10 минут простоя
    DOWNTIME_MAX_POSTS: int = 5  # Максимум постов после простоя

    # ✅ ИНТЕРВАЛ ПРОВЕРКИ YOUTUBE
    YOUTUBE_PARSING_INTERVAL: int = 1800  # 30 минут

    # ✅ FSM STATE TTL (время жизни состояний)
    FSM_STATE_TTL: int = 300  # 5 минут (тест), 86400 (продакшен), 0 (без TTL)

    @property
    def database_url_async(self) -> str:
        if self.DATABASE_URL:
            if not self.DATABASE_URL.startswith('postgresql+asyncpg://'):
                return self.DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://')
            return self.DATABASE_URL
        raise ValueError("DATABASE_URL не найден в настройках")


settings = Settings()