import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import telegram
from bs_config import Env

from bot.config import load_config_dict_from_yaml
from bot.rules.rule import Rule

_LOG = logging.getLogger(__name__)


@dataclass
class Config:
    enabled_chats: list[int]


class PremiumRule(Rule):
    @classmethod
    def name(cls) -> str:
        return "premium"

    def __init__(self, config_dir: Path, secrets_env: Env):
        self.config = self._load_config(config_dir)

    @staticmethod
    def _load_config(config_dir: Path) -> Config:
        config_dict = load_config_dict_from_yaml(config_dir / "premium.yaml")

        if not config_dict:
            _LOG.warning("Config file is empty or missing.")
            return Config(
                enabled_chats=[],
            )

        return Config(
            enabled_chats=[
                int(chat_id) for chat_id in config_dict.get("enabledChats", [])
            ],
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
        if chat_id not in self.config.enabled_chats:
            _LOG.debug("Not enabled in %d", chat_id)
            return

        user = message.from_user
        if user is None:
            _LOG.debug("No user found")
            return

        if user.is_premium:
            _LOG.debug("User has premium: %s", user.id)
            return

        await message.chat.ban_member(
            user_id=user.id,
            revoke_messages=False,
            until_date=datetime.now(tz=UTC) + timedelta(minutes=1),
        )
