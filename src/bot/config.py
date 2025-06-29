import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Self

import yaml
from bs_config import Env
from bs_nats_updater import NatsConfig

_LOG = logging.getLogger(__name__)


def load_config_dict_from_yaml(config_file: Path) -> dict | None:
    if not config_file.is_file():
        return None

    with config_file.open("r", encoding="utf-8") as f:
        config_dict = yaml.load(f, yaml.Loader)
        if not config_dict:
            return None

    return config_dict


@dataclass
class KubernetesStateConfig:
    name_prefix: str
    namespace: str

    @classmethod
    def from_env(cls, env: Env) -> Self | None:
        namespace = env.get_string("NAMESPACE")
        if namespace is None:
            return None

        return cls(
            namespace=namespace,
            name_prefix=env.get_string("NAME_PREFIX", required=True),
        )


@dataclass
class RedisStateConfig:
    host: str
    username: str
    password: str

    @classmethod
    def from_env(cls, env: Env) -> Self | None:
        host = env.get_string("HOST")
        if host is None:
            return None

        return cls(
            host=host,
            username=env.get_string("USERNAME", required=True),
            password=env.get_string("PASSWORD", required=True),
        )


@dataclass
class StateConfig:
    kubernetes: KubernetesStateConfig | None
    redis: RedisStateConfig | None

    @classmethod
    def from_env(cls, env: Env) -> Self:
        if env.get_bool("DEBUG_MODE", default=False):
            _LOG.warning("Debug mode enabled")
            return cls(
                kubernetes=None,
                redis=None,
            )

        return cls(
            kubernetes=KubernetesStateConfig.from_env(env.scoped("KUBERNETES_")),
            redis=RedisStateConfig.from_env(env.scoped("REDIS_")),
        )


@dataclass
class Config:
    app_version: str
    config_dir: Path
    nats: NatsConfig | None
    rule_base_env: Env
    sentry_dsn: str | None
    state: StateConfig
    telegram_token: str

    @classmethod
    def from_env(cls, env: Env) -> Self:
        return cls(
            app_version=env.get_string("APP_VERSION", default="dirty"),
            config_dir=Path(env.get_string("CONFIG_DIR", default="config")),
            nats=NatsConfig.from_env(env.scoped("NATS_"), is_optional=True),
            rule_base_env=env.scoped("RULE_"),
            sentry_dsn=env.get_string("SENTRY_DSN"),
            state=StateConfig.from_env(env.scoped("STATE_")),
            telegram_token=env.get_string("TELEGRAM_API_KEY", required=True),
        )
