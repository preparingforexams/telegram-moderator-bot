import asyncio
import contextlib
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Self, Callable

from bs_config import Env
from telegram import Bot
from telegram.error import TelegramError
from telegram.ext import Updater as LegacyUpdater

FAKE= LegacyUpdater


@dataclass
class NatsConfig:
    url:str
    consumer_name: str
    receiver_secret: str
    stream_name: str

    @classmethod
    def from_env(cls, env: Env)->Self:
        return cls(
            url=env.get_string("SERVER_URL"),
            consumer_name=env.get_string("CONSUMER_NAME"),
            receiver_secret=env.get_string("RECEIVER_SECRET"),
            stream_name=env.get_string("STREAM_NAME"),
        )

class NatsUpdater(contextlib.AbstractAsyncContextManager["NatsUpdater"]):
    def __init__(self, *, bot: Bot, nats_config: NatsConfig)->None:
        self.update_queue: asyncio.Queue[object] = asyncio.Queue()
        self.bot = bot
        self.nats_config = nats_config

    # TODO: running property?

    async def initialize(self) -> None:
        pass

    async def shutdown(self) -> None:
        pass
    async def start_polling(
            self,
            poll_interval: float = 0.0,
            timeout: int = 10,
            bootstrap_retries: int = 0,
            allowed_updates: Sequence[str] |None = None,
            drop_pending_updates: bool |None = None,
            error_callback: Callable[[TelegramError], None]|None = None,
        ) -> asyncio.Queue[object]:
        pass
