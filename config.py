from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    OPENAI_API_KEY: str
    NODE_ENV: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_DATABASE: str
    POSTGRES_PORT: str = "5432"  # Default port for PostgreSQL
    
    # Telegram linking configuration
    BACKEND_API_KEY: str = "your-secure-api-key-here"
    BACKEND_JWT_SECRET: str = "your-jwt-secret-here"
    BACKEND_JWT_AUDIENCE: str = "telegram-link"
    FRONTEND_BASE_URL: str = "http://localhost:3000"
    SESSION_SECRET: str = "your-session-secret-here"

    # Construct the full URL dynamically
    @property
    def POSTGRES_URL(self):
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DATABASE}"
        )

    model_config = SettingsConfigDict(env_file=".env.development", extra="ignore")


settings = Settings()
