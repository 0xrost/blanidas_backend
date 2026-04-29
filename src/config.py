from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from pydantic import Field, BaseModel, DirectoryPath
from pydantic_settings import BaseSettings, SettingsConfigDict

class MailTemplate(BaseModel):
    subject_file: str
    content_file: str

class SMTPSettings(BaseModel):
    server: str
    port: int

    username: str
    password: str

    from_address: str

    templates_dir: DirectoryPath
    low_stock_template: MailTemplate
    repair_request_created_template: MailTemplate
    health_check_template: MailTemplate

class JWTSettings(BaseModel):
    secret_key: str = Field(min_length=64)
    algorithm: str = "HS256"
    refresh_token_expire_minutes: int
    access_token_expire_minutes: int

class AppSettings(BaseSettings):
    database_url: str
    jwt: JWTSettings
    smtp: SMTPSettings
    static_files_dir: str
    proxy_url_to_static_files_dir: str
    client_url: str

    superuser_email: str
    superuser_password: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__"
    )

@lru_cache
def get_settings() -> AppSettings:
    return AppSettings()

SettingsDep = Annotated[AppSettings, Depends(get_settings)]

def get_jwt_settings(settings: SettingsDep) -> JWTSettings:
    return settings.jwt

JWTSettingsDep = Annotated[JWTSettings, Depends(get_jwt_settings)]

def get_smtp_settings(settings: SettingsDep) -> SMTPSettings:
    return settings.smtp

SMTPSettingsDep = Annotated[SMTPSettings, Depends(get_smtp_settings)]
