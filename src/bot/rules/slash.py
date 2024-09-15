import logging
import re
from os import path
from pathlib import Path
from typing import Optional, Set

from bot import telegram
from bot.rules import Rule

_LOG = logging.getLogger(__name__)


class SlashRule(Rule):
    @property
    def name(self) -> str:
        return "command_spam"

    def __init__(self, config_dir: Path):
        self.config = self._load_config(config_dir)

    @staticmethod
    def _load_config(config_dir: Path) -> Set[int]:
        file_path = path.join(str(config_dir), "slash.txt")

        if not path.isfile(file_path):
            _LOG.warning("No config found")
            return set()

        with open(file_path, "r") as f:
            lines = f.readlines()

        return {int(line.strip()) for line in lines}

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
        if not self._is_enabled(chat_id):
            _LOG.debug("Not enabled in %d", chat_id)
            return

        text: Optional[str] = message.get("text")

        if text and self._is_plain_command(text):
            _LOG.info("Detected plain command. Deleting...")
            await telegram.delete_message(message)

    def _is_enabled(self, chat_id: int) -> bool:
        return chat_id in self.config

    @staticmethod
    def _is_plain_command(text: str) -> bool:
        pattern = re.compile(r"/\w+")
        return bool(pattern.fullmatch(text))
