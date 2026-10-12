from typing import Literal
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    flight_provider: Literal['demo', 'duffel_test'] = 'demo'
    duffel_access_token: str = ''
    groq_api_key: SecretStr = SecretStr('')
    groq_model: str = 'openai/gpt-oss-120b'
    database_url: str = 'sqlite:///./flight_agent.db'
    cors_origin: str = 'http://localhost:5173'


settings = Settings()
