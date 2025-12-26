from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # App
    APP_NAME: str = "Yalla Trip"
    DEBUG: bool = False

    # LLM Provider: "ollama" or "openai"
    LLM_PROVIDER: str = "ollama"
    LLM_MODEL: str = "llama3.2:3b"
    CONTEXT_WINDOW_TURNS: int = 5

    # Ollama (local)
    OLLAMA_BASE_URL: str = "http://localhost:11434/v1"

    # OpenAI (cloud)
    OPENAI_API_KEY: str = ""

    # Persistence
    DB_PATH: str = "yalla_trip.db"


settings = Settings()
