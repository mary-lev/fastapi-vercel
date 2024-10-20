from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    OPENAI_API_KEY: str
    NODE_ENV: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_DATABASE: str
    POSTGRES_PORT: str = "5432"  # Default port for PostgreSQL

    # Construct the full URL dynamically
    @property
    def POSTGRES_URL(self):
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DATABASE}"
        )

    model_config = SettingsConfigDict(
        env_file=".env.development",
        extra="ignore"
    )

settings = Settings()
