from pydantic_settings import BaseSettings

class Config(BaseSettings):
    bot_token: str
    postgres_dsn: str
    openai_api_key: str
    telegram_api_id: int
    telegram_api_hash: str

    class Config:
        env_file = ".env"

config = Config()
