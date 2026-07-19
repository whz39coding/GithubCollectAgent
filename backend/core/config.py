from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = BACKEND_ROOT / ".env"


class Settings(BaseSettings):
    send_message_flag: bool = Field(default=False, alias="SEND_MESSAGE")
    check_github_api : bool =Field(default=False,alias="CHECK_GITHUB_API")
    github_token: str | None = Field(default=None, alias="GITHUB_TOKEN")
    llm_api_key: str = Field(alias="LLM_API_KEY")
    llm_base_url: str = Field(alias="LLM_BASE_URL")
    llm_model: str = Field(alias="LLM_MODEL")
    feishu_webhook: str | None = Field(default=None, alias="FEISHU_WEBHOOK")
    legacy_notifier_webhook: str | None = Field(default=None, alias="NOTIFIER_WEBHOOK")

    trending_language: str = Field(alias="TRENDING_LANGUAGE")
    trending_since: Literal["daily", "weekly", "monthly"] = Field(alias="TRENDING_SINCE")
    analysis_num: int = Field(alias="ANALYSIS_NUM")
    readme_max_length: int = Field(alias="README_MAX_LENGTH")
    save_readme: bool = Field(alias="SAVE_README")
    prompt_template_path: Path = Field(alias="PROMPT_TEMPLATE_PATH")

    log_dir: Path = Field(alias="LOG_DIR")
    database_url: str = Field(alias="DATABASE_URL")
    final_report_path: Path = Field(default="final_report.txt", alias="FINAL_REPORT_PATH")

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @field_validator("prompt_template_path", "log_dir", "final_report_path", mode="after")
    @classmethod
    def resolve_project_path(cls, value: Path) -> Path:
        if value.is_absolute():
            return value
        return PROJECT_ROOT / value

    @property
    def notifier_webhook(self) -> str | None:
        return self.feishu_webhook or self.legacy_notifier_webhook


@lru_cache
def get_settings() -> Settings:
    return Settings()
