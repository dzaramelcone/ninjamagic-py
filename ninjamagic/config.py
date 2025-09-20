from pydantic import BaseModel, Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class OAuthSettings(BaseModel):
    client: str
    secret: str


class Settings(BaseSettings):
    google: OAuthSettings = Field(default_factory=OAuthSettings)
    discord: OAuthSettings
    allow_local_auth: bool = False
    pg: PostgresDsn
    model_config = SettingsConfigDict(
        env_nested_delimiter="__", env_file="ninjamagic.env"
    )


settings = Settings()
