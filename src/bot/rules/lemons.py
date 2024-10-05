import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Self

import telegram
from bs_config import Env

from bot.config import load_config_dict_from_yaml
from bot.rules.rule import Rule

_LOG = logging.getLogger(__name__)


@dataclass
class _Config:
    enabled_chat_ids: list[int]

    @classmethod
    def from_dict(cls, config_dict: dict) -> Self:
        return cls(
            enabled_chat_ids=config_dict["enabledChats"],
        )


class LemonRule(Rule):
    @classmethod
    def name(cls) -> str:
        return "lemons"

    @staticmethod
    def _load_config(config_dir: Path) -> _Config:
        config_dict = load_config_dict_from_yaml(config_dir / "lemons.yaml")

        if not config_dict:
            _LOG.warning("Config is empty or missing")
            return _Config([])

        return _Config.from_dict(config_dict)

    def __init__(self, config_dir: Path, secrets_env: Env):
        self._config = self._load_config(config_dir)

    def initial_state(self) -> None:
        pass

    async def __call__(
        self,
        *,
        chat_id: int,
        message: telegram.Message,
        is_edited: bool,
        state: None,
    ) -> None:
        if chat_id not in self._config.enabled_chat_ids:
            return
        _LOG.debug("Enabled in chat %d", chat_id)

        if (dice := message.dice) and dice.emoji == "🎰":
            dice_value = dice.value

            # 43 is lemon, lemon, lemon
            if dice_value != 43:
                return

            _LOG.info("Found matching message")
            await message.reply_photo(
                photo="AgACAgIAAxkBAANCZubaqbSkbSosatNb5P1AMlLE1uEAAhe1MRsINDlJu4Nokvml5S8BAAMCAAN4AAM2BA",
            )
