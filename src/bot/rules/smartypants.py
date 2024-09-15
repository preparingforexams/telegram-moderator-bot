import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Self

from bot.config import load_config_dict_from_yaml
from bot.rules import Rule

_LOG = logging.getLogger(__name__)


@dataclass
class _Config:
    enabled_chat_ids: list[int]
    openai_token: str

    @classmethod
    def from_dict(cls, config_dict: dict) -> Self:
        return cls(
            enabled_chat_ids=config_dict["enabledChats"],
            openai_token=config_dict["OPENAI_TOKEN"],
        )

    @classmethod
    def disabled(cls) -> Self:
        return cls(
            enabled_chat_ids=[],
            openai_token="",
        )


class SmartypantsRule(Rule[None]):
    @property
    def name(self) -> str:
        return "smartypants"

    def __init__(self, config_dir: Path, secrets: dict[str, str]):
        self.config = self._load_config(config_dir, secrets)

    @staticmethod
    def _load_config(config_dir: Path, secrets: dict[str, str]) -> _Config:
        config_dict = load_config_dict_from_yaml(config_dir / "smartypants.yaml")

        if not config_dict:
            _LOG.warning("Config is empty or missing")
            return _Config.disabled()

        return _Config.from_dict({**secrets, **config_dict})

    def initial_state(self) -> None:
        pass

    async def __call__(
        self,
        *,
        chat_id: int,
        message: dict,
        is_edited: bool,
        state: None,
    ) -> None:
        if chat_id not in self.config.enabled_chat_ids:
            _LOG.debug("Disabled in chat %d", chat_id)
            return

        _LOG.warning("Not implemented yet")
