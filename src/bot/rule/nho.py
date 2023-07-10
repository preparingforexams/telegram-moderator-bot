from __future__ import annotations

import logging
from dataclasses import dataclass
from os import path
from typing import List

import yaml

from bot import telegram
from bot.rule.rule import Rule

_LOG = logging.getLogger(__name__)


@dataclass
class _Config:
    enabled_chat_ids: List[int]

    @classmethod
    def from_dict(cls, config_dict: dict) -> _Config:
        return cls(
            enabled_chat_ids=config_dict["enabledChats"],
        )


class NhoRule(Rule):
    name = "nho"

    @staticmethod
    def _load_config(config_dir: str) -> _Config:
        file_path = path.join(config_dir, "nho.yaml")
        if not path.isfile(file_path):
            _LOG.warning("No config found")
            return _Config([])

        with open(file_path, "r", encoding="utf-8") as f:
            config_dict = yaml.load(f, yaml.Loader)
            if not config_dict:
                _LOG.warning("Config is empty")
                return _Config([])

        return _Config.from_dict(config_dict)

    def __init__(self, config_dir: str):
        self._config = self._load_config(config_dir)

    def __call__(self, chat_id: int, message: dict, is_edited: bool) -> None:
        if chat_id not in self._config.enabled_chat_ids:
            return
        _LOG.debug("Enabled in chat %d", chat_id)

        sender = message["from"]
        if sender["is_bot"] and sender["username"] == "@nnnnnnnnhhhhhhhhbot":
            _LOG.info("Trying to delete bot message")
            if not telegram.delete_message(message):
                _LOG.warning("Failed to prevent our horrible fate")
