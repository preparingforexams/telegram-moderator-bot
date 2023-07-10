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

    @classmethod
    def from_dict(cls, config_dict: dict) -> Self:
        return cls(
            enabled_chat_ids=config_dict["enabledChats"],
        )


class SmartypantsRule(Rule):
    @property
    def name(self) -> str:
        return "smartypants"

    def __init__(self, config_dir: str):
        self.config = self._load_config(config_dir)

    @staticmethod
    def _load_config(config_dir: str) -> _Config:
        file_path = path.join(config_dir, "smartypants.yaml")
        if not path.isfile(file_path):
            _LOG.warning("No config found")
            return _Config([])

        with open(file_path, "r", encoding="utf-8") as f:
            config_dict = yaml.load(f, yaml.Loader)
            if not config_dict:
                _LOG.warning("Config is empty")
                return _Config([])

        return _Config.from_dict(config_dict)

    def __call__(self, chat_id: int, message: dict, is_edited: bool) -> None:
        if chat_id not in self.config.enabled_chat_ids:
            _LOG.debug("Disabled in chat %d", chat_id)
            return

        _LOG.warning("Not implemented yet")
