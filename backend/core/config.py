from functools import lru_cache
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = BACKEND_ROOT / ".env"

import os
# 显式加载 .env 以更新 os.environ，保证 requests 等第三方库能够读取到代理变量
load_dotenv(dotenv_path=ENV_FILE)

# 【关键修复】Linux 系统下 Python 的 requests 库严格依赖小写的环境变量（http_proxy/https_proxy）。
# 无论是在前端 UI 配置，还是 .env 文件中，通常是大写。这里强制把大写同步给小写，防止代理失效。
if os.environ.get("HTTP_PROXY"):
    os.environ["http_proxy"] = os.environ["HTTP_PROXY"]
if os.environ.get("HTTPS_PROXY"):
    os.environ["https_proxy"] = os.environ["HTTPS_PROXY"]


class Settings(BaseSettings):
    send_message_flag: bool = Field(default=False, alias="SEND_MESSAGE")
    check_github_api : bool =Field(default=False,alias="CHECK_GITHUB_API")
    github_token: str | None = Field(default=None, alias="GITHUB_TOKEN")
    llm_api_key: str = Field(alias="LLM_API_KEY")
    llm_base_url: str = Field(alias="LLM_BASE_URL")
    llm_model: str = Field(alias="LLM_MODEL")
    feishu_webhook: str | None = Field(default=None, alias="FEISHU_WEBHOOK")
    legacy_notifier_webhook: str | None = Field(default=None, alias="NOTIFIER_WEBHOOK")
    http_proxy: str | None = Field(default=None, alias="HTTP_PROXY")
    https_proxy: str | None = Field(default=None, alias="HTTPS_PROXY")

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
