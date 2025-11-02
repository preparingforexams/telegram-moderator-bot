import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Self

from bs_nats_updater import NatsConfig

if TYPE_CHECKING:
    from bs_config import Env

_LOG = logging.getLogger(__name__)


@dataclass
class RedisStateConfig:
    host: str
    username: str
    password: str

    @classmethod
    def from_env(cls, env: Env) -> Self | None:
        host = env.get_string("host")
        if host is None:
            return None

        return cls(
            host=host,
            username=env.get_string("username", required=True),
            password=env.get_string("password", required=True),
        )


@dataclass
class StateConfig:
    redis: RedisStateConfig | None

    @classmethod
    def from_env(cls, env: Env) -> Self:
        if env.get_bool("debug-mode", default=False):
            _LOG.warning("Debug mode enabled")
            return cls(
                redis=None,
            )

        return cls(
            redis=RedisStateConfig.from_env(env / "redis"),
        )


@dataclass
class Config:
    app_version: str
    config_dir: Path
    nats: NatsConfig | None
    sentry_dsn: str | None
    state: StateConfig
    telegram_token: str

    @classmethod
    def from_env(cls, env: Env) -> Self:
        return cls(
            app_version=env.get_string("app-version", default="dirty"),
            config_dir=Path(env.get_string("config-dir", default="config")),
            nats=NatsConfig.from_env(env / "nats", is_optional=True),
            sentry_dsn=env.get_string("sentry-dsn"),
            state=StateConfig.from_env(env / "state"),
            telegram_token=env.get_string("telegram-api-key", required=True),
        )
