import asyncio
import logging
import sys
from dataclasses import dataclass
from typing import Generic, TypeVar

import sentry_sdk
from bs_config import Env
from bs_state import StateStorage
from bs_state.implementation import config_map_storage
from pydantic import BaseModel

from bot import rules, telegram
from bot.config import Config
from bot.events import rules as event_rule
from bot.events.rule import EventRule
from bot.events.subscriber import EventSubscriber

_LOG = logging.getLogger("bot")

S = TypeVar("S", bound=BaseModel)


@dataclass
class RuleState(Generic[S]):
    rule: rules.Rule[S]
    state_storage: StateStorage[S] | None  # type: ignore[type-var]


async def _handle_updates(rule_list: list[RuleState]) -> None:
    async def _on_update(update: dict):
        message = update.get("message")
        edited_message = update.get("edited_message")

        if not (message or edited_message):
            _LOG.debug("Skipping non-message update")
            return

        effective_message: dict = message or edited_message  # type: ignore
        chat_id = effective_message["chat"]["id"]

        for rule_state in rule_list:
            rule = rule_state.rule
            _LOG.debug("Loading state for rule %s", rule.name)
            state_storage = rule_state.state_storage
            if state_storage is not None:
                state = await state_storage.load()
                old_state = state.model_copy(deep=True)
            else:
                state = None
                old_state = None

            _LOG.debug("Passing message to rule %s", rule.name)
            try:
                await rule(
                    chat_id=chat_id,
                    message=effective_message,
                    is_edited=edited_message is not None,
                    state=state,
                )
            except Exception as e:
                _LOG.error("Rule threw an exception", exc_info=e)
            else:
                if state_storage is not None and old_state != state:
                    await state_storage.store(state)

    await telegram.handle_updates(_on_update)


async def _load_state_storage(
    config: Config,
    rule: rules.Rule[S | None],
) -> StateStorage[S] | None:
    initial_state = rule.initial_state()
    if initial_state is None:
        return None

    state_config = config.state
    if state_config is None:
        from bs_state.implementation import memory_storage

        return await memory_storage.load(initial_state=initial_state)
    else:
        name_prefix = state_config.secret_name_prefix
        namespace = state_config.secret_namespace

        name = f"{name_prefix}{rule.name}"

        return await config_map_storage.load(
            initial_state=initial_state,
            namespace=namespace,
            config_map_name=name,
        )


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
            rule_base_env.scoped(RuleClass.name().upper()),
        )
        for RuleClass in rule_classes
    ]

    return [
        RuleState(rule, await _load_state_storage(config, rule))
        for rule in initialized_rules
    ]


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
    await _handle_updates(rule_states)


def _load_config() -> Config:
    env = Env.load()
    return Config.from_env(env)


def main() -> None:
    _setup_logging()

    config = _load_config()
    telegram.initialize(config.telegram_token)

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
            config=subscriber_config,
            rule=handler,
        )
        subscriber.subscribe()
    else:
        asyncio.run(_run_telegram_bot(config))


if __name__ == "__main__":
    main()
