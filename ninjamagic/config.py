from uuid import uuid4

from pydantic import BaseModel, Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class OAuthSettings(BaseModel):
    client: str
    secret: str


class Settings(BaseSettings):
    google: OAuthSettings = Field(default_factory=OAuthSettings)
    discord: OAuthSettings
    pg: PostgresDsn
    session_secret: str
    allow_local_auth: bool = False
    use_vite_proxy: bool = False
    log_level: str = "WARNING"
    random_seed: str = Field(default_factory=lambda: str(uuid4()))
    learn_abmode: tuple[float, float, float] = (0.0, 60.0, 15.0)

    model_config = SettingsConfigDict(
        env_nested_delimiter="__", env_file="ninjamagic.env"
    )


settings = Settings()
