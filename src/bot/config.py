import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Self

import yaml
from bs_config import Env

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
class StateConfig:
    secret_name_prefix: str
    secret_namespace: str

    @classmethod
    def from_env(cls, env: Env) -> Self | None:
        if env.get_bool("DEBUG_MODE", default=False):
            _LOG.warning("Debug mode enabled")
            return None

        return cls(
            secret_name_prefix=env.get_string("NAME_PREFIX", required=True),
            secret_namespace=env.get_string("NAMESPACE", required=True),
        )


@dataclass
class SubscriberConfig:
    subscription_name: str

    @classmethod
    def from_env(cls, env: Env) -> Self | None:
        project_id = env.get_string("GOOGLE_CLOUD_PROJECT")
        simple_sub_name = env.get_string("GOOGLE_PUBSUB_SUBSCRIPTION")

        if not (project_id and simple_sub_name):
            return None

        return cls(
            subscription_name=f"projects/{project_id}/subscriptions/{simple_sub_name}",
        )


@dataclass
class Config:
    app_version: str
    config_dir: Path
    rule_base_env: Env
    sentry_dsn: str | None
    state: StateConfig | None
    subscriber: SubscriberConfig | None
    telegram_token: str

    @classmethod
    def from_env(cls, env: Env) -> Self:
        return cls(
            app_version=env.get_string("APP_VERSION", default="dirty"),
            config_dir=Path(env.get_string("CONFIG_DIR", default="config")),
            rule_base_env=env.scoped("RULE_"),
            sentry_dsn=env.get_string("SENTRY_DSN"),
            state=StateConfig.from_env(env.scoped("STATE_")),
            subscriber=SubscriberConfig.from_env(env),
            telegram_token=env.get_string("TELEGRAM_API_KEY", required=True),
        )
