from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field, PostgresDsn, RedisDsn

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="../.env",
        env_ignore_empty=True,
        extra="ignore"
    )
    # general variables
    DEBUG: bool = True
    MAX_API_CALL_TIMEOUT: int = 300
    ALLOWED_DOMAINS: set = {"ripplelinks.com"}

    # google apps script related variables, won't start without these
    APPS_SCRIPT_API_SECRET: str
    APPS_SCRIPT_API_URL: str

    # DB variables
    DB_TYPE: str = "postgresql"
    DB_DRIVER: str = "asyncpg"
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 5432
    DB_USERNAME: str = ""
    DB_PASSWORD: str =""
    DB_NAME: str = ""

    @computed_field
    @property
    def DB_URL(self) -> PostgresDsn:
        return PostgresDsn.build(
            scheme=f"{self.DB_TYPE}+{self.DB_DRIVER}",
            host=self.DB_HOST,
            port=self.DB_PORT,
            username=self.DB_USERNAME,
            password=self.DB_PASSWORD,
            path=self.DB_NAME,
        )

    @computed_field
    @property
    def DB_URL_MIGRATION(self) -> PostgresDsn:
        return PostgresDsn.build(
            scheme=f"{self.DB_TYPE}+psycopg2",
            host=self.DB_HOST,
            port=self.DB_PORT,
            username=self.DB_USERNAME,
            password=self.DB_PASSWORD,
            path=self.DB_NAME,
        )

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    @computed_field
    @property
    def REDIS_URL(self) -> RedisDsn:
        return RedisDsn.build(
            scheme="redis",
            host=self.REDIS_HOST,
            port=self.REDIS_PORT,
            path="0"
        )


settings = Settings()
