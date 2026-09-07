from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator
from urllib.parse import urlsplit


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="NOTETAKER_", env_file=".env", extra="ignore")
    database_url: str = "postgresql+psycopg://notetaker:development@127.0.0.1:5432/notetaker"
    preview: bool = False
    web_origin: str = "http://127.0.0.1:3000"
    allowed_hosts: list[str] = ["127.0.0.1", "localhost", "api"]
    secure_cookies: bool = False
    session_hours: int = 24
    s3_endpoint: str = "http://127.0.0.1:8333"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    audio_bucket: str = "notetaker-audio"
    speech_model_path: str = ".local/models/faster-whisper-small.en"
    speech_threads: int = 4
    kafka_bootstrap: str = "127.0.0.1:9092"

    @model_validator(mode="after")
    def validate_mode(self):
        origin=urlsplit(self.web_origin)
        if origin.scheme not in ('http','https') or not origin.hostname or origin.path or origin.query or origin.fragment:
            raise ValueError('Set a single web origin without a path')
        if origin.scheme=='http' and origin.hostname not in ('127.0.0.1','localhost'):
            raise ValueError('Non-loopback web origins require HTTPS')
        if origin.scheme=='https' and not self.secure_cookies:
            raise ValueError('HTTPS requires secure session cookies')
        if self.database_url.startswith("sqlite") and not self.preview:
            raise ValueError("SQLite requires explicit NOTETAKER_PREVIEW=true; production uses PostgreSQL")
        if not self.database_url.startswith(("sqlite", "postgresql+psycopg://")):
            raise ValueError("Unsupported database driver")
        return self
