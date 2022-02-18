from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from os import path
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

import yaml

from bot import telegram
from bot.rule.rule import Rule

_LOG = logging.getLogger(__name__)


@dataclass
class _ChatConfig:
    emojis: List[str]
    cooldown: Optional[timedelta]

    def is_cooled_down(self, last: datetime, now: datetime) -> bool:
        cooldown = self.cooldown
        if cooldown is not None:
            time_diff = abs(now - last)
            return time_diff > cooldown
        else:
            berlin = ZoneInfo('Europe/Berlin')
            local_last = last.astimezone(berlin)
            local_now = now.astimezone(berlin)

            return local_last.day != local_now.day

    @classmethod
    def from_dict(cls, config_dict: dict) -> _ChatConfig:
        emojis = config_dict.get('emojis', [])
        cooldown_dict = config_dict.get('cooldown', None)
        if cooldown_dict is None:
            return _ChatConfig(emojis, None)

        if not cooldown_dict:
            raise ValueError('Not cooldown specified')

        cooldown = timedelta(
            days=cooldown_dict.get('days', 0),
            hours=cooldown_dict.get('hours', 0),
            minutes=cooldown_dict.get('minutes', 0),
            seconds=cooldown_dict.get('seconds', 0),
        )

        return _ChatConfig(
            emojis=emojis,
            cooldown=cooldown,
        )


@dataclass
class _Config:
    config_by_chat_id: Dict[int, _ChatConfig]

    @classmethod
    def from_dict(cls, config_dict: dict) -> _Config:
        config_by_chat_id = {
            key: _ChatConfig.from_dict(value)
            for key, value in config_dict.items()
        }
        return _Config(
            config_by_chat_id=config_by_chat_id,
        )


class DartsRule(Rule):
    name = "darts"

    def __init__(self, config_dir: str):
        self._last_dart: Dict[int, datetime] = {}
        self._config = self._load_config(config_dir)

    @staticmethod
    def _load_config(config_dir: str) -> _Config:
        file_path = path.join(config_dir, "darts.yaml")
        if not path.isfile(file_path):
            _LOG.warning("No config found")
            return _Config({})

        with open(file_path, 'r', encoding='utf-8') as f:
            config_dict = yaml.load(f, yaml.Loader)
            if not config_dict:
                _LOG.warning("Config is empty")
                return _Config({})

        return _Config.from_dict(config_dict)

    def __call__(self, chat_id: int, message: dict) -> None:
        config = self._config.config_by_chat_id.get(chat_id)
        if not config:
            _LOG.debug("Not enabled in chat %d", chat_id)
            return

        dice = message.get('dice')
        if not dice:
            return

        if dice['emoji'] not in config.emojis:
            _LOG.debug("Dice emoji %s was not in %s", dice['emoji'], config.emojis)
            return

        user = message['from']
        username = user['first_name']
        user_id = user['id']

        message_time = datetime.fromtimestamp(message['date'], tz=timezone.utc)
        last_message = self._last_dart.get(user_id)
        self._last_dart[user_id] = message_time

        if not last_message:
            _LOG.debug("No known last message from user %s", username)
            return

        if config.is_cooled_down(last=last_message, now=message_time):
            _LOG.debug("Cooldown expired")
            return

        _LOG.info("Deleting message from user %s", username)
        telegram.delete_message(message)
