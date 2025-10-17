import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from io import StringIO
from pathlib import Path
from typing import Self, cast
from zoneinfo import ZoneInfo

import telegram
from bs_config import Env
from pydantic import BaseModel

from bot.config import load_config_dict_from_yaml
from bot.rules.rule import Rule

_DUO_IDS = frozenset({167930454, 389582243})
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


@dataclass(frozen=True)
class DartResult:
    time: datetime
    # TODO: remove None after migration
    result: int | None


class LastDarts(BaseModel):
    dart_result_by_user_id: dict[int, int] = {}
    dart_time_by_user_id: dict[int, datetime] = {}

    def get_darts(self, user_id: int) -> DartResult | None:
        time = self.dart_time_by_user_id.get(user_id)
        if time is None:
            return None

        result = self.dart_result_by_user_id.get(user_id)
        return DartResult(time=time, result=result)


class DuoStats(BaseModel):
    count_same: int = 1
    count_different: int = 0


class DartsState(BaseModel):
    last_darts_by_chat_id: dict[int, LastDarts] = {}
    duo_stats_by_chat_id: dict[int, DuoStats] = {}

    def get_last_dart(self, *, chat_id: int, user_id: int) -> DartResult | None:
        last_darts = self.last_darts_by_chat_id.get(chat_id, LastDarts())
        return last_darts.get_darts(user_id)

    def get_duo_stats(self, *, chat_id: int) -> DuoStats:
        stats = self.duo_stats_by_chat_id.get(chat_id)

        if stats is None:
            stats = DuoStats()
            self.duo_stats_by_chat_id[chat_id] = stats

        return stats

    def put_dart(
        self,
        *,
        chat_id: int,
        user_id: int,
        time: datetime,
        result: int,
    ) -> None:
        last_darts = self.last_darts_by_chat_id.get(chat_id)
        if last_darts is None:
            last_darts = LastDarts()
            self.last_darts_by_chat_id[chat_id] = last_darts

        last_darts.dart_time_by_user_id[user_id] = time
        last_darts.dart_result_by_user_id[user_id] = result


class DartsRule(Rule[DartsState]):
    @classmethod
    def name(cls) -> str:
        return "darts"

    def __init__(self, config_dir: Path, secrets_env: Env):
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

    @staticmethod
    def _is_valid(
        config: _ChatConfig,
        last_dart: DartResult | None,
        darts_time: datetime,
    ) -> bool:
        if not last_dart:
            _LOG.debug("No last dart found")
            return True

        if config.is_cooled_down(last=last_dart.time, now=darts_time):
            _LOG.debug("Cooldown expired")
            return True

        return False

    @staticmethod
    def is_command(*, command_name: str, message: str) -> bool:
        is_command = message.startswith("/")
        if not is_command:
            return False

        parts = message.split(maxsplit=1)
        if len(parts) != 1:
            raise ValueError("Did not expect args")

        return message == f"/{command_name}" or message.startswith(f"/{command_name}@")

    async def __call__(
        self,
        *,
        chat_id: int,
        message: telegram.Message,
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

        if dice := message.dice:
            await self._handle_dice_message(
                chat_id=chat_id, config=config, message=message, state=state, dice=dice
            )
            return

        if text := message.text:
            try:
                is_command = self.is_command(command_name="stats", message=text)
            except ValueError as e:
                _LOG.info("Received invalid command: %s", e)
                await message.set_reaction("🤷🏻‍♂️")
            else:
                if is_command:
                    await self._handle_stats_command(
                        chat_id=chat_id, message=message, state=state
                    )

    async def _handle_dice_message(
        self,
        *,
        chat_id: int,
        config: _ChatConfig,
        message: telegram.Message,
        state: DartsState,
        dice: telegram.Dice,
    ) -> None:
        if dice.emoji not in config.emojis:
            _LOG.debug("Dice emoji %s was not in %s", dice.emoji, config.emojis)
            return

        user = cast(telegram.User, message.from_user)
        username = user.first_name
        user_id = user.id

        message_time = message.date
        last_dart = state.get_last_dart(chat_id=chat_id, user_id=user_id)

        if not self._is_valid(config, last_dart, message_time):
            _LOG.info("Deleting message from user %s", username)
            await message.delete()
            return

        state.put_dart(
            chat_id=chat_id,
            user_id=user_id,
            time=message_time,
            result=dice.value,
        )

        duo_ids = list(_DUO_IDS)
        if user_id not in duo_ids:
            return

        duo_ids.remove(user_id)
        other_id = duo_ids[0]
        other_result = state.get_last_dart(chat_id=chat_id, user_id=other_id)

        if other_result is None or config.is_cooled_down(
            last=other_result.time, now=message_time
        ):
            _LOG.debug("Not tracking stats as duo isn't complete today")
            return

        stats = state.get_duo_stats(chat_id=chat_id)
        if other_result.result == dice.value:
            stats.count_same += 1
        else:
            stats.count_different += 1

    async def _handle_stats_command(
        self, *, chat_id: int, message: telegram.Message, state: DartsState
    ) -> None:
        user = cast(telegram.User, message.from_user)
        if user.id not in _DUO_IDS:
            _LOG.debug("Ignoring command for user %s", user.id)
            await message.delete()
            return

        start_date = date(2025, 9, 26)
        today = datetime.now(tz=ZoneInfo("Europe/Berlin")).date()
        days_observed = (today - start_date).days + 1

        stats = state.get_duo_stats(chat_id=chat_id)
        days_with_stats = stats.count_same + stats.count_different
        if days_with_stats == 0:
            await message.set_reaction("🤷🏻‍♂️")
            return

        quota = (stats.count_same / days_with_stats) * 100.0

        response = StringIO()
        response.write(f"Tage seit Start der Erfassung: {days_observed}\n")
        response.write(f"Tage mit Würfen von beiden: {days_with_stats}\n")
        response.write(f"🤝-Quote: {quota:.1f}%\n")
        if quota < (100.0 / 6.0):
            response.write("\nL")

        await message.reply_text(response.getvalue())
