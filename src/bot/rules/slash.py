import logging
import re
from pathlib import Path

from bs_config import Env

from bot import telegram
from bot.rules import Rule

_LOG = logging.getLogger(__name__)


class SlashRule(Rule):
    @classmethod
    def name(cls) -> str:
        return "command_spam"

    def __init__(self, config_dir: Path, secrets_env: Env):
        self.config = self._load_config(config_dir)

    @staticmethod
    def _load_config(config_dir: Path) -> set[int]:
        file_path = config_dir / "slash.txt"

        if not file_path.is_file():
            _LOG.warning("No config found")
            return set()

        with file_path.open("r") as f:
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

        text: str | None = message.get("text")

        if text and self._is_plain_command(text):
            _LOG.info("Detected plain command. Deleting...")
            await telegram.delete_message(message)

    def _is_enabled(self, chat_id: int) -> bool:
        return chat_id in self.config

    @staticmethod
    def _is_plain_command(text: str) -> bool:
        pattern = re.compile(r"/\w+")
        return bool(pattern.fullmatch(text))
