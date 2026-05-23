"""Configuration loading from config.json."""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FeishuConfig:
    """Feishu bot credentials and settings."""
    app_id: str = ""
    app_secret: str = ""
    encrypt_key: str = ""
    verification_token: str = ""


@dataclass
class CardConfig:
    """Lark-card style card template settings."""
    title: str = "AI Assistant"
    template: str = "blue"
    footer: str = "Powered by Neolix AI"


@dataclass
class LlmConfig:
    """LLM provider settings."""
    base_url: str = "https://claude.neolix.ai"
    api_key: str = ""
    model: str = "claude-opus-4.6-vertex"
    max_tokens: int = 4096
    system_prompt: str = "You are a helpful assistant."


@dataclass
class AppConfig:
    """Top-level application configuration."""
    feishu: FeishuConfig = field(default_factory=FeishuConfig)
    llm: LlmConfig = field(default_factory=LlmConfig)
    card: CardConfig = field(default_factory=CardConfig)


def LoadConfig(path: str | None = None) -> AppConfig:
    """Load configuration from a JSON file.

    Searches in order:
      1. Explicit ``path`` argument
      2. ``CONFIG_PATH`` environment variable
      3. ``config.json`` in the current working directory
    """
    if path is None:
        path = os.environ.get("CONFIG_PATH", "config.json")

    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, encoding="utf-8") as f:
        raw = json.load(f)

    feishu_raw = raw.get("feishu", {})
    llm_raw = raw.get("llm", {})
    card_raw = raw.get("card", {})

    feishu_cfg = FeishuConfig(
        app_id=feishu_raw.get("app_id", ""),
        app_secret=feishu_raw.get("app_secret", ""),
        encrypt_key=feishu_raw.get("encrypt_key", ""),
        verification_token=feishu_raw.get("verification_token", ""),
    )

    llm_cfg = LlmConfig(
        base_url=llm_raw.get("base_url", LlmConfig.base_url),
        api_key=llm_raw.get("api_key", ""),
        model=llm_raw.get("model", LlmConfig.model),
        max_tokens=llm_raw.get("max_tokens", LlmConfig.max_tokens),
        system_prompt=llm_raw.get("system_prompt", LlmConfig.system_prompt),
    )

    card_cfg = CardConfig(
        title=card_raw.get("title", CardConfig.title),
        template=card_raw.get("template", CardConfig.template),
        footer=card_raw.get("footer", CardConfig.footer),
    )

    return AppConfig(feishu=feishu_cfg, llm=llm_cfg, card=card_cfg)
