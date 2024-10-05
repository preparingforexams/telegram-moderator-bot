import asyncio
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from tempfile import NamedTemporaryFile

from bs_config import Env

from bot import telegram
from bot.config import load_config_dict_from_yaml
from bot.rules.rule import Rule

from .detector import SkyDetector

_LOG = logging.getLogger(__name__)


class Action(Enum):
    insight = "insight"
    reply = "reply"
    delete = "delete"


@dataclass
class Config:
    enabled_chats: set[int]
    actions: list[Action]


class SkyRule(Rule):
    @classmethod
    def name(cls) -> str:
        return "sky"

    def __init__(self, config_dir: Path, secret_env: Env):
        self.config = self._load_config(config_dir)
        self.detector = SkyDetector()

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
        if chat_id not in self.config.enabled_chats:
            _LOG.debug("Not enabled in chat %d", chat_id)
            return

        photos: list[dict] | None = message.get("photo")
        if not photos:
            _LOG.debug("Message has no photo")
            return

        largest_photo_id = self._find_largest_photo(photos)
        loop = asyncio.get_running_loop()
        with NamedTemporaryFile("w+b") as file:
            await telegram.download_file(largest_photo_id, file)
            file.seek(0)
            detected, sky_file = await loop.run_in_executor(
                None,
                self.detector.detect,
                file,
            )

        try:
            for action in self.config.actions:
                if action == Action.insight:
                    await self._give_insight(chat_id, message, sky_file)
                elif not detected and action == Action.reply:
                    await self._reply(chat_id, message)
                elif not detected and action == Action.delete:
                    await self._delete(chat_id, message)
        finally:
            if sky_file:
                sky_file.unlink()

    @staticmethod
    def _find_largest_photo(photos: list[dict]) -> str:
        # We can only download up to 20 MB
        available_photos = (
            photo for photo in photos if photo["file_size"] < 20_000_000
        )
        max_photo = max(available_photos, key=lambda photo: photo["file_size"])
        return max_photo["file_id"]

    @staticmethod
    async def _reply(chat_id: int, message: dict):
        await telegram.send_message(
            chat_id,
            text="Ich glaube da war nicht genug Himmel!",
            reply_to_message_id=message["message_id"],
        )

    @staticmethod
    async def _delete(chat_id: int, message: dict):
        if not await telegram.delete_message(message):
            _LOG.error("Could not delete message in chat %d", chat_id)

    @staticmethod
    async def _give_insight(chat_id: int, message: dict, image_path: Path):
        with image_path.open("rb") as f:
            await telegram.send_image(
                chat_id,
                f,
                "Das hier habe ich an Himmel gefunden...",
                reply_to_message_id=message["message_id"],
            )

    @staticmethod
    def _load_config(config_dir: Path) -> Config:
        config_dict = load_config_dict_from_yaml(config_dir / "sky.yaml")

        if not config_dict:
            _LOG.warning("Config is empty or missing.")
            return Config(
                enabled_chats=set(),
                actions=[],
            )

        return Config(
            enabled_chats=set(config_dict["enabledChats"]),
            actions=[Action(it) for it in config_dict["actions"]],
        )
