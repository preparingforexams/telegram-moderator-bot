import logging
from dataclasses import dataclass
from os import path
from typing import Self

import yaml

from bot.rule import Rule

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


class SmartypantsRule(Rule):
    @property
    def name(self) -> str:
        return "smartypants"

    def __init__(self, config_dir: str, secrets: dict[str, str]):
        self.config = self._load_config(config_dir, secrets)

    @staticmethod
    def _load_config(config_dir: str, secrets: dict[str, str]) -> _Config:
        file_path = path.join(config_dir, "smartypants.yaml")
        if not path.isfile(file_path):
            _LOG.warning("No config found")
            return _Config.disabled()

        with open(file_path, "r", encoding="utf-8") as f:
            config_dict = yaml.load(f, yaml.Loader)
            if not config_dict:
                _LOG.warning("Config is empty")
                return _Config.disabled()

        return _Config.from_dict({**secrets, **config_dict})

    def __call__(self, chat_id: int, message: dict, is_edited: bool) -> None:
        if chat_id not in self.config.enabled_chat_ids:
            _LOG.debug("Disabled in chat %d", chat_id)
            return

        _LOG.warning("Not implemented yet")
