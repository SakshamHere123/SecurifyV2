from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    PROJECT_NAME: str = "Securify"
    ENV: str = "development"

    # Database
    DATABASE_URL: str = "postgresql://securify:securify@db:5432/securify"

    # Redis (used starting Phase 7, defined now so config is centralized)
    REDIS_URL: str = "redis://redis:6379/0"

    # LLM / embeddings (OpenAI). Analyzer/remediation agents join in Phase 4;
    # embeddings are needed now, in Phase 3, to build the RAG index.
    OPENAI_API_KEY: str = ""

    # Auth (Phase 6). SECRET must be overridden in .env for anything beyond
    # local dev -- this default exists so the app doesn't crash on first run.
    JWT_SECRET_KEY: str = "change-me-in-env"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    class Config:
        env_file = ".env"


settings = Settings()