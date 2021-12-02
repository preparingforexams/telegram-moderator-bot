import logging
import os
from dataclasses import dataclass
from enum import Enum
from os import path
from tempfile import NamedTemporaryFile
from typing import List, Set, Optional

import yaml

from bot import telegram
from bot.rule.rule import Rule
from .detector import SkyDetector

_LOG = logging.getLogger(__name__)


class Action(Enum):
    insight = "insight"
    reply = "reply"
    delete = "delete"


@dataclass
class Config:
    enabled_chats: Set[int]
    actions: List[Action]


class SkyRule(Rule):
    @property
    def name(self) -> str:
        return "sky"

    def __init__(self, config_dir: str):
        self.config = self._load_config(config_dir)
        self.detector = SkyDetector()

    def __call__(self, chat_id: int, message: dict):
        if chat_id not in self.config.enabled_chats:
            _LOG.debug("Not enabled in chat %d", chat_id)
            return

        photos: Optional[List[dict]] = message.get("photo")
        if not photos:
            _LOG.debug("Message has no photo")
            return

        largest_photo_id = self._find_largest_photo(photos)
        with NamedTemporaryFile("w+b") as file:
            telegram.download_file(largest_photo_id, file)
            file.seek(0)
            detected, sky_file = self.detector.detect(file)

        try:
            for action in self.config.actions:
                if action == Action.insight:
                    self._give_insight(chat_id, message, sky_file)
                elif not detected and action == Action.reply:
                    self._reply(chat_id, message)
                elif not detected and action == Action.delete:
                    self._delete(chat_id, message)
        finally:
            if sky_file:
                os.remove(sky_file)

    @staticmethod
    def _find_largest_photo(photos: List[dict]) -> str:
        # We can only download up to 20 MB
        available_photos = (photo for photo in photos if photo["file_size"] < 20_000_000)
        max_photo = max(available_photos, key=lambda photo: photo["file_size"])
        return max_photo["file_id"]

    @staticmethod
    def _reply(chat_id: int, message: dict):
        telegram.send_message(
            chat_id,
            text="Ich glaube da war nicht genug Himmel!",
            reply_to_message_id=message["message_id"],
        )

    @staticmethod
    def _delete(chat_id: int, message: dict):
        if not telegram.delete_message(message):
            _LOG.error("Could not delete message in chat %d", chat_id)

    @staticmethod
    def _give_insight(chat_id: int, message: dict, image_path: str):
        with open(image_path, "rb") as f:
            telegram.send_image(
                chat_id,
                f,
                "Das hier habe ich an Himmel gefunden...",
                reply_to_message_id=message["message_id"],
            )

    @staticmethod
    def _load_config(config_dir: str) -> Config:
        with open(path.join(config_dir, "sky.yaml"), "r") as f:
            raw = yaml.load(f, yaml.Loader)

        return Config(
            enabled_chats=set(raw["enabledChats"]),
            actions=[Action(it) for it in raw["actions"]],
        )
