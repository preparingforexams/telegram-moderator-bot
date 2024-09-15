import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Self
from zoneinfo import ZoneInfo

from pydantic import BaseModel

from bot import telegram
from bot.config import load_config_dict_from_yaml
from bot.rules.rule import Rule

_LOG = logging.getLogger(__name__)


@dataclass
class _ChatConfig:
    emojis: list[str]
    cooldown: timedelta | None

    def is_cooled_down(self, last: datetime, now: datetime) -> bool:
        cooldown = self.cooldown
        if cooldown is not None:
            time_diff = abs(now - last)
            return time_diff > cooldown
        else:
            berlin = ZoneInfo("Europe/Berlin")
            local_last = last.astimezone(berlin)
            local_now = now.astimezone(berlin)

            return local_last.day != local_now.day

    @classmethod
    def from_dict(cls, config_dict: dict) -> Self:
        emojis = config_dict.get("emojis", [])
        cooldown_dict = config_dict.get("cooldown", None)
        if cooldown_dict is None:
            return cls(emojis, None)

        if not cooldown_dict:
            raise ValueError("Not cooldown specified")

        cooldown = timedelta(
            days=cooldown_dict.get("days", 0),
            hours=cooldown_dict.get("hours", 0),
            minutes=cooldown_dict.get("minutes", 0),
            seconds=cooldown_dict.get("seconds", 0),
        )

        return cls(
            emojis=emojis,
            cooldown=cooldown,
        )


@dataclass
class _Config:
    config_by_chat_id: dict[int, _ChatConfig]

    @classmethod
    def from_dict(cls, config_dict: dict) -> Self:
        config_by_chat_id = {
            key: _ChatConfig.from_dict(value) for key, value in config_dict.items()
        }
        return cls(
            config_by_chat_id=config_by_chat_id,
        )


class LastDarts(BaseModel):
    dart_time_by_user_id: dict[int, datetime] = {}


class DartsState(BaseModel):
    last_darts_by_chat_id: dict[int, LastDarts] = {}

    def get_last_dart(self, *, chat_id: int, user_id: int) -> datetime | None:
        last_darts = self.last_darts_by_chat_id.get(chat_id, LastDarts())
        return last_darts.dart_time_by_user_id.get(user_id)

    def put_dart(self, *, chat_id: int, user_id: int, time: datetime) -> None:
        last_darts = self.last_darts_by_chat_id.get(chat_id)
        if last_darts is None:
            last_darts = LastDarts()
            self.last_darts_by_chat_id[chat_id] = last_darts

        last_darts.dart_time_by_user_id[user_id] = time


class DartsRule(Rule[DartsState]):
    name = "darts"

    def __init__(self, config_dir: Path):
        self._config = self._load_config(config_dir)

    @staticmethod
    def _load_config(config_dir: Path) -> _Config:
        config_dict = load_config_dict_from_yaml(config_dir / "darts.yaml")

        if not config_dict:
            _LOG.warning("Config is empty or missing")
            return _Config({})

        return _Config.from_dict(config_dict)

    def initial_state(self) -> DartsState:
        return DartsState()

    async def __call__(
        self,
        *,
        chat_id: int,
        message: dict,
        is_edited: bool,
        state: DartsState,
    ) -> None:
        config = self._config.config_by_chat_id.get(chat_id)
        if not config:
            _LOG.debug("Not enabled in chat %d", chat_id)
            return

        if is_edited:
            _LOG.info("Skipping edited message")
            return

        dice = message.get("dice")
        if not dice:
            return

        if dice["emoji"] not in config.emojis:
            _LOG.debug("Dice emoji %s was not in %s", dice["emoji"], config.emojis)
            return

        user = message["from"]
        username = user["first_name"]
        user_id = user["id"]

        message_time = datetime.fromtimestamp(message["date"], tz=UTC)
        last_dart_time = state.get_last_dart(chat_id=chat_id, user_id=user_id)
        state.put_dart(chat_id=chat_id, user_id=user_id, time=message_time)

        if not last_dart_time:
            _LOG.debug(
                "No known last message from user %s in chat %d", username, chat_id
            )
            return

        if config.is_cooled_down(last=last_dart_time, now=message_time):
            _LOG.debug("Cooldown expired")
            return

        _LOG.info("Deleting message from user %s", username)
        await telegram.delete_message(message)
