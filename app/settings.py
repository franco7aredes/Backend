import os
from functools import lru_cache


class Settings:
    """Configuración de la aplicación Centralizada.
    """

    # URL de la base de datos (async)
    DATABASE_URL_ASYNC: str = os.getenv(
        "DATABASE_URL_ASYNC", "sqlite+aiosqlite:///./db.sqlite"
    )

    # CORS
    CORS_ORIGINS: list[str] = [
        os.getenv("CORS_ORIGIN_1", "http://localhost:5173"),
        os.getenv("CORS_ORIGIN_2", "http://localhost:5174"),
        os.getenv("CORS_ORIGIN_3", "http://127.0.0.1:8000"),
        os.getenv("CORS_ORIGIN_4", "http://localhost:3000"),
        os.getenv("CORS_ORIGIN_5", "http://localhost:3001"),
    ]


@lru_cache
def get_settings() -> Settings:
    return Settings()


# Instancia global de settings
settings = get_settings()
