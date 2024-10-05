from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import telegram

from bot.events.rule import EventRule

_LOG = logging.getLogger(__name__)


@dataclass
class HoroscopeEvent:
    chat_id: int
    message_id: int
    user_id: int
    horoscope: str

    @classmethod
    def deserialize(cls, event: dict) -> HoroscopeEvent:
        return cls(
            chat_id=event["chat_id"],
            message_id=event["message_id"],
            user_id=event["user_id"],
            horoscope=event["horoscope"],
        )


class IdolRule(EventRule):
    @classmethod
    def name(cls) -> str:
        return "idol"

    def __init__(self, config_dir: Path):
        pass

    async def __call__(self, bot: telegram.Bot, event: dict) -> bool:
        data = HoroscopeEvent.deserialize(event)

        _LOG.debug("Looking at horoscope %s", data.horoscope)

        if "Idol" not in data.horoscope:
            _LOG.debug("No idols found, skipping")
            return True

        await bot.send_message(
            chat_id=data.chat_id,
            text="Balek?!",
            reply_to_message_id=data.message_id,
        )

        return True
