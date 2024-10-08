import logging
from dataclasses import dataclass
from pathlib import Path

import telegram
from bs_config import Env

from bot.config import load_config_dict_from_yaml
from bot.rules.rule import Rule

_LOG = logging.getLogger(__name__)


@dataclass
class Config:
    forward_to: int | None
    allowed_emojis: dict[int, set[str]]


class DiceRule(Rule):
    @classmethod
    def name(cls) -> str:
        return "casino"

    def __init__(self, config_dir: Path, secrets_env: Env):
        self.config = self._load_config(config_dir)

    @staticmethod
    def _load_config(config_dir: Path) -> Config:
        config_dict = load_config_dict_from_yaml(config_dir / "dice.yaml")

        if not config_dict:
            _LOG.warning("Config file is empty or missing.")
            return Config(
                forward_to=None,
                allowed_emojis={},
            )

        return Config(
            forward_to=config_dict.get("forwardTo"),
            allowed_emojis={
                chat_id: set(emojis)
                for chat_id, emojis in config_dict.get("allowedEmojis", {}).items()
            },
        )

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
        allowed_emojis = self.config.allowed_emojis.get(chat_id)
        if allowed_emojis is None:
            _LOG.debug("Not enabled in %d", chat_id)
            return

        dice = message.dice

        if dice and dice.emoji not in allowed_emojis:
            _LOG.info("Detected forbidden dice %s.", dice["emoji"])
            if self.config.forward_to:
                _LOG.debug("Forwarding messages")
                await self._forward(message, to_chat_id=self.config.forward_to)
            await message.delete()

    async def _forward(self, message: telegram.Message, to_chat_id: int) -> None:
        reply_message = message.reply_to_message
        if reply_message:
            _LOG.debug("Forwarding replied-to message as well")
            await reply_message.forward(chat_id=to_chat_id)
        await message.forward(chat_id=to_chat_id)
