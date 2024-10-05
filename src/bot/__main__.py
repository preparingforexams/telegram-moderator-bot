import asyncio
import logging
import sys

import sentry_sdk
import telegram
from bs_config import Env

from bot import rules
from bot.config import Config
from bot.events import rules as event_rule
from bot.events.rule import EventRule
from bot.events.subscriber import EventSubscriber
from bot.rule_state import RuleState
from bot.telegram_bot import TelegramBot

_LOG = logging.getLogger("bot")


async def _init_rules(config: Config) -> list[RuleState]:
    config_dir = config.config_dir
    rule_base_env = config.rule_base_env

    rule_classes = [
        rules.DartsRule,
        rules.DiceRule,
        rules.LemonRule,
        rules.SkyRule,
        rules.SlashRule,
        rules.SmartypantsRule,
    ]

    initialized_rules = [
        RuleClass(  # type: ignore[abstract]
            config_dir,
            rule_base_env.scoped(f"{RuleClass.name().upper()}_"),
        )
        for RuleClass in rule_classes
    ]

    return list(
        filter(
            None,
            [await RuleState.load(rule, config) for rule in initialized_rules],
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


async def _run_telegram_bot(config: Config):
    rule_states = await _init_rules(config)
    bot = TelegramBot(config, rule_states)
    await bot.run()


def _load_config() -> Config:
    env = Env.load()
    return Config.from_env(env)


def main() -> None:
    _setup_logging()

    config = _load_config()

    _setup_sentry(config)

    args = sys.argv
    if len(args) > 1:
        arg = args[1]

        config_dir = config.config_dir
        handler: EventRule
        if arg == "--subscribe-horoscopes":
            handler = event_rule.IdolRule(config_dir)
        else:
            _LOG.error("Invalid arguments (%s)", args)
            sys.exit(1)

        subscriber_config = config.subscriber
        if subscriber_config is None:
            _LOG.error("Subscriber config is missing or incomplete")
            sys.exit(1)

        subscriber = EventSubscriber(
            bot=telegram.Bot(config.telegram_token),
            config=subscriber_config,
            rule=handler,
        )
        subscriber.subscribe()
    else:
        asyncio.run(_run_telegram_bot(config))


if __name__ == "__main__":
    main()
