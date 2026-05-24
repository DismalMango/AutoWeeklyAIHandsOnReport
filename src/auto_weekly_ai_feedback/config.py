from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


class ConfigError(RuntimeError):
    """Raised when required runtime configuration is missing."""


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    openai_base_url: str | None
    model_name: str
    tavily_api_key: str

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()

        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
        missing = []
        if not api_key:
            missing.append("OPENAI_API_KEY or DEEPSEEK_API_KEY")
        missing.extend(
            name for name in ("MODEL_NAME", "TAVILY_API_KEY") if not os.getenv(name)
        )
        if missing:
            names = ", ".join(missing)
            raise ConfigError(f"Missing required environment variable(s): {names}")

        return cls(
            openai_api_key=api_key,
            openai_base_url=os.getenv("OPENAI_BASE_URL") or None,
            model_name=os.environ["MODEL_NAME"],
            tavily_api_key=os.environ["TAVILY_API_KEY"],
        )
