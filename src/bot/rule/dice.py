import logging
from dataclasses import dataclass
from os import path
from typing import Set, Dict, Optional

import yaml

from bot import telegram
from bot.rule.rule import Rule

_LOG = logging.getLogger(__name__)


@dataclass
class Config:
    forward_to: Optional[int]
    allowed_emojis: Dict[int, Set[str]]


class DiceRule(Rule):
    @property
    def name(self) -> str:
        return "casino"

    def __init__(self, config_dir: str):
        self.config = self._load_config(config_dir)

    @staticmethod
    def _load_config(config_dir: str) -> Config:
        file_path = path.join(config_dir, "dice.yaml")
        if not path.isfile(file_path):
            _LOG.warning("No config found")
            return Config(forward_to=None, allowed_emojis={})

        with open(file_path, "r") as f:
            raw: dict = yaml.load(f, yaml.Loader)

        return Config(
            forward_to=raw.get("forwardTo"),
            allowed_emojis={
                chat_id: set(emojis)
                for chat_id, emojis in raw.get("allowedEmojis", {}).items()
            },
        )

    def __call__(self, chat_id: int, message: dict, is_edited: bool):
        allowed_emojis = self.config.allowed_emojis.get(chat_id)
        if allowed_emojis is None:
            _LOG.debug("Not enabled in %d", chat_id)
            return

        dice: Optional[dict] = message.get("dice")

        if dice and dice["emoji"] not in allowed_emojis:
            _LOG.info("Detected forbidden dice %s.", dice["emoji"])
            if self.config.forward_to:
                _LOG.debug("Forwarding messages")
                self._forward(message, to_chat_id=self.config.forward_to)
            telegram.delete_message(message)

    def _forward(self, message: dict, to_chat_id: int):
        reply_message: Optional[dict] = message.get("reply_to_message")
        if reply_message:
            _LOG.debug("Forwarding replied-to message as well")
            telegram.forward_message(to_chat_id=to_chat_id, message=reply_message)
        telegram.forward_message(to_chat_id=to_chat_id, message=message)
