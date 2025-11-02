import logging
import re

import telegram
from bs_config import Env

from bot.rules import Rule

_LOG = logging.getLogger(__name__)


class SlashRule(Rule):
    @classmethod
    def name(cls) -> str:
        return "command-spam"

    def __init__(self, env: Env) -> None:
        self._enabled_chats = env.get_int_list("enabled-chats", default=[])

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
        if not self._is_enabled(chat_id):
            _LOG.debug("Not enabled in %d", chat_id)
            return

        text = message.text

        if text and self._is_plain_command(text):
            _LOG.info("Detected plain command. Deleting...")
            await message.delete()

    def _is_enabled(self, chat_id: int) -> bool:
        return chat_id in self._enabled_chats

    @staticmethod
    def _is_plain_command(text: str) -> bool:
        pattern = re.compile(r"/\w+")
        return bool(pattern.fullmatch(text))
