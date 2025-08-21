
from pydantic import AnyHttpUrl, BaseModel, Field, SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine.url import URL
from functools import lru_cache
from pathlib import Path
import logging.config

PROJECT_DIR = Path(__file__).parent.parent.parent

class Security(BaseModel):
    jwt_issuer: str = "routeapi"
    jwt_secret_key: SecretStr = SecretStr("sk-change-me")
    jwt_access_token_expire_secs: int = 3600  # 1h
    jwt_cookie_secure: bool = True
    jwt_refresh_token_expire_secs: int = 24 * 3600  # 1d
    jwt_refresh_token_location: list[str] = ["headers", "cookies"]
    password_bcrypt_rounds: int = 12
    allowed_hosts: list[str] = ["localhost", "127.0.0.1"]
    backend_cors_origins: list[AnyHttpUrl] = []

class Database(BaseModel):
    hostname: str = "postgres"
    username: str = "postgres"
    password: SecretStr = SecretStr("passwd-change-me")
    port: int = 5432
    db: str = "postgres"

class Settings(BaseSettings):
    security: Security = Field(default_factory=Security)
    database: Database = Field(default_factory=Database)
    log_level: str = "INFO"

    @computed_field 
    @property
    def sqlalchemy_database_uri(self) -> URL:
 
        return URL.create(
            drivername="postgresql+asyncpg",
            username=self.database.username,
            password=self.database.password.get_secret_value(),
            host=self.database.hostname,
            port=self.database.port,
            database=self.database.db,
        )
    
    model_config = SettingsConfigDict(
        env_file=f"{PROJECT_DIR}/.env",
        case_sensitive=False,
        env_nested_delimiter="__",
    )

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

def logging_config(log_level: str) -> None:

    conf = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "verbose": {
                "format": "{asctime} [{levelname}] {name}: {message}",
                "style": "{",
            },
        },        
        "handlers": {
            "stream": {
                "class": "logging.StreamHandler",
                "formatter": "verbose",
                "level": "DEBUG",
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "verbose",
                "level": "INFO",
                "filename": "routeapi.log",      # Log file path
                "maxBytes": 10485760,            # 10 MB
                "backupCount": 5,                # Keep last 5 files
                "encoding": "utf8"
            },
        },
        "loggers": {
            "": {
                "level": log_level,
                "handlers": ["stream","file"],
                "propagate": False,
            },
        },
    }
    logging.config.dictConfig(conf)

logging_config(log_level=get_settings().log_level)