from pydantic_settings import BaseSettings
from pydantic import ValidationError


class Config(BaseSettings):
    bot_token: str
    postgres_dsn: str
    openai_api_key: str
    telegram_api_id: int
    telegram_api_hash: str
    log_level: str = "INFO"

    class Config:
        env_file = ".env"


def validate_config() -> None:
    """
    Базовая валидация обязательных полей и типов.
    Бросает ValidationError/ValueError при проблемах.
    """
    missing = []
    for field in ["bot_token", "postgres_dsn", "openai_api_key", "telegram_api_id", "telegram_api_hash"]:
        if not getattr(config, field, None):
            missing.append(field)
    if missing:
        raise ValidationError(f"Missing required settings: {', '.join(missing)}", Config)

    if config.telegram_api_id <= 0:
        raise ValueError("telegram_api_id must be positive")


config = Config()
