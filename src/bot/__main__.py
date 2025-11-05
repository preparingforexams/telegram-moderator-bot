import asyncio
import logging
from typing import TYPE_CHECKING

import sentry_sdk
import uvloop
from bs_config import Env

from bot import rules
from bot.config import Config, StateConfig
from bot.rule_state import RuleState
from bot.telegram_bot import TelegramBot

if TYPE_CHECKING:
    from pathlib import Path

_LOG = logging.getLogger("bot")


async def _init_rules(
    state_config: StateConfig | None, rules_env: Env
) -> list[RuleState]:
    rule_classes = [
        rules.DartsRule,
        rules.LemonRule,
        rules.PremiumRule,
        rules.SlashRule,
    ]

    initialized_rules = [
        RuleClass(  # type: ignore[abstract]
            rules_env / RuleClass.name(),
        )
        for RuleClass in rule_classes
    ]

    return list(
        filter(
            None,
            [await RuleState.load(rule, state_config) for rule in initialized_rules],
        )
    )


def _setup_logging():
    logging.basicConfig()
    _LOG.level = logging.DEBUG


def _setup_sentry(config: Config):
    dsn = config.sentry_dsn
    if not dsn:
        _LOG.warning("Sentry DSN not found")
        return

    sentry_sdk.init(
        dsn,
        release=config.app_version,
    )


async def _run_telegram_bot(config: Config, rules_env: Env) -> None:
    rule_states = await _init_rules(config.state, rules_env)
    bot = TelegramBot(config, rule_states)
    try:
        await bot.run()
    finally:
        async with asyncio.TaskGroup() as tg:
            for rule_state in rule_states:
                state_storage = rule_state.state_storage
                if state_storage is not None:
                    tg.create_task(state_storage.close())


def _load_config() -> Config:
    env = Env.load()
    return Config.from_env(env)


def _load_rules_env(config_dir: Path) -> Env:
    toml_paths = []
    for file in config_dir.iterdir():
        if file.is_file() and file.name.endswith(".toml"):
            toml_paths.append(file)

    env = Env.load(
        toml_configs=toml_paths,
    )
    return env / "rule"


def main() -> None:
    _setup_logging()
    config = _load_config()
    _setup_sentry(config)

    rules_env = _load_rules_env(config.config_dir)

    uvloop.run(_run_telegram_bot(config, rules_env))


if __name__ == "__main__":
    main()
