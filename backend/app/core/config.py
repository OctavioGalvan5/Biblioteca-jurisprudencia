from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración de la aplicación"""

    # Base de datos
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/jurisprudencia"

    # MinIO
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET_NAME: str = "sentencias"
    MINIO_SECURE: bool = False

    # OpenAI
    OPENAI_API_KEY: str = ""

    # Anthropic Claude
    ANTHROPIC_API_KEY: str = ""

    # App
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = True

    # CORS
    FRONTEND_URL: str = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )


settings = Settings()
