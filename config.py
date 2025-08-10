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

    # CORS configuration - comma-separated list of allowed origins
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001,http://localhost:3002,http://localhost:8000,https://frontend-template-lilac.vercel.app,https://dhdk.vercel.app"

    # API server URLs for OpenAPI spec - JSON format
    API_SERVER_URLS: str = '[{"url": "http://localhost:8000", "description": "Development server"}, {"url": "https://dhdk.vercel.app", "description": "Production server"}]'

    # Professor configuration (temporary - should move to database)
    # TODO: Move professor information to database model instead of configuration
    PROFESSOR_INFO: str = '{"id": 1, "img": "/images/client/avatar-02.png", "name": "Silvio Peroni", "type": "Director of Second Cycle Degree in Digital Humanities and Digital Knowledge", "desc": "Associate Professor / Department of Classical Philology and Italian Studies", "social": [{"link": "https://x.com/essepuntato", "icon": "twitter"}, {"link": "https://www.linkedin.com/in/essepuntato/", "icon": "linkedin"}]}'

    # Testing configuration
    TEST_API_BASE_URL: str = "http://localhost:8000"

    # Construct the full URL dynamically
    @property
    def POSTGRES_URL(self):
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DATABASE}"
        )

    model_config = SettingsConfigDict(
        env_file=".env.development", extra="ignore")


settings = Settings()
