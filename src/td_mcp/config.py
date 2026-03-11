"""Configuration via environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    td_host: str = "127.0.0.1"
    td_port: int = 9980
    td_timeout: float = 10.0

    @property
    def td_base_url(self) -> str:
        return f"http://{self.td_host}:{self.td_port}"


settings = Settings()
