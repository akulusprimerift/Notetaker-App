from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, model_validator
from urllib.parse import urlsplit
from pathlib import Path
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="NOTETAKER_", env_file=".env", extra="ignore")
    database_url: str = Field(default_factory=lambda: 'sqlite:///' + (Path.cwd() / '.local/workspace.sqlite3').as_posix())
    preview: bool = False
    standalone: bool = True
    audio_directory: str = Field(default_factory=lambda: str(Path.cwd() / '.local/audio'))
    web_origin: str = "http://127.0.0.1:3000"
    allowed_hosts: list[str] = ["127.0.0.1", "localhost"]
    secure_cookies: bool = False
    session_hours: int = 24
    speech_model_path: str = ".local/models/faster-whisper-small.en"
    speech_threads: int = 4
    speech_live_beam_size: int = Field(default=1, ge=1, le=5)
    speech_status_path: str = ''
    speech_status_session: str = ''
    ollama_url: str = "http://127.0.0.1:11434"
    provider_directory: str = ''
    provider_bridge_url: str = ''
    provider_bridge_token: str = ''

    @model_validator(mode="after")
    def validate_mode(self):
        model_url = urlsplit(self.ollama_url)
        if (model_url.scheme != 'http' or model_url.hostname not in ('127.0.0.1', 'localhost')
                or model_url.username or model_url.password or model_url.path or model_url.query or model_url.fragment):
            raise ValueError('The local note provider must use a local Ollama endpoint')
        if self.provider_bridge_url:
            bridge = urlsplit(self.provider_bridge_url)
            if (bridge.scheme != 'http' or bridge.hostname not in ('127.0.0.1', 'localhost')
                    or bridge.username or bridge.password or bridge.path not in ('', '/') or bridge.query or bridge.fragment
                    or not self.provider_bridge_token or len(self.provider_bridge_token) < 32):
                raise ValueError('The provider bridge must use an authenticated local HTTP endpoint')
        origin=urlsplit(self.web_origin)
        if origin.scheme not in ('http','https') or not origin.hostname or origin.path or origin.query or origin.fragment:
            raise ValueError('Set a single web origin without a path')
        if origin.scheme=='http' and origin.hostname not in ('127.0.0.1','localhost'):
            raise ValueError('Non-loopback web origins require HTTPS')
        if origin.scheme=='https' and not self.secure_cookies:
            raise ValueError('HTTPS requires secure session cookies')
        url = make_url(self.database_url)
        if url.drivername != 'sqlite' or url.host or url.query:
            raise ValueError('Notetaker requires a local SQLite database')
        if not self.preview and (not url.database or not Path(url.database).is_absolute()):
            raise ValueError('The library requires an absolute SQLite database file path')
        if not Path(self.audio_directory).is_absolute():
            raise ValueError('The library requires an absolute audio directory')
        return self
