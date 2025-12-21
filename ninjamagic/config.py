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

    save_character_rate: float = 5.0 * 60.0
    regen_tick_rate: float = 5.0

    attack_len: float = 3.0
    block_len: float = 1.2
    block_miss_len: float = 2.5
    stun_len: float = 5.0

    base_proc_odds: float = 0.10

    model_config = SettingsConfigDict(
        env_nested_delimiter="__", env_file="ninjamagic.env"
    )


settings = Settings()
