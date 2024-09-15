import json
import logging
from dataclasses import dataclass
from os import path
from typing import List, Self

import yaml

from bot import telegram
from bot.rules.rule import Rule

_LOG = logging.getLogger(__name__)


@dataclass
class _Config:
    enabled_chat_ids: List[int]

    @classmethod
    def from_dict(cls, config_dict: dict) -> Self:
        return cls(
            enabled_chat_ids=config_dict["enabledChats"],
        )


class LemonRule(Rule):
    name = "lemons"

    @staticmethod
    def _load_config(config_dir: str) -> _Config:
        file_path = path.join(config_dir, "lemons.yaml")
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
        if chat_id not in self._config.enabled_chat_ids:
            return
        _LOG.debug("Enabled in chat %d", chat_id)

        if photo := message.get("photo"):
            await telegram.send_message(
                chat_id=chat_id,
                text=json.dumps(photo, indent=4),
                reply_to_message_id=message.get("message_id"),
            )

        if (dice := message.get("dice")) and dice["emoji"] == "🎰":
            dice_value = dice["value"]

            # 43 is lemon, lemon, lemon
            if dice_value != 43:
                return

            _LOG.info("Found matching message")
            await telegram.send_existing_image(
                chat_id=chat_id,
                file_id="AgACAgIAAxkBAAIMIWbm08i7ATRGgOQSO7foaZsrdx9VAAIXtTEbCDQ5SVcm8KvdjhlzAQADAgADeAADNgQ",
                reply_to_message_id=message["message_id"],
            )
