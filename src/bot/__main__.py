import asyncio
import logging
import os
import sys
from dataclasses import dataclass
from typing import Generic, List, TypeVar

import sentry_sdk
from bs_state import StateStorage
from bs_state.implementation import config_map_storage
from pydantic import BaseModel

from bot import rules, telegram
from bot.events import rules as event_rule
from bot.events.rule import EventRule
from bot.events.subscriber import EventSubscriber

_ADMIN_USER_ID = os.getenv("ADMIN_USER_ID")
_CONFIG_DIRECTORY = os.getenv("CONFIG_DIR")

_LOG = logging.getLogger("bot")

S = TypeVar("S", bound=BaseModel)


@dataclass
class RuleState(Generic[S]):
    rule: rules.Rule[S]
    state_storage: StateStorage[S] | None  # type: ignore[type-var]


def _handle_updates(rule_list: list[RuleState]) -> None:
    def _on_update(update: dict):
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
            # TODO: run in async context
            state_storage = rule_state.state_storage
            if state_storage is not None:
                state = asyncio.run(state_storage.load())
                old_state = state.model_copy(deep=True)
            else:
                state = None
                old_state = None

            _LOG.debug("Passing message to rule %s", rule.name)
            try:
                rule(
                    chat_id,
                    effective_message,
                    is_edited=edited_message is not None,
                    state=state,
                )
            except Exception as e:
                _LOG.error("Rule threw an exception", exc_info=e)
            else:
                if state_storage is not None and old_state != state:
                    asyncio.run(state_storage.store(state))

    telegram.handle_updates(_on_update)


def _load_state_storage(rule: rules.Rule[S | None]) -> StateStorage[S] | None:
    initial_state = rule.initial_state()
    if initial_state is None:
        return None

    if os.getenv("DEBUG_MODE"):
        from bs_state.implementation import memory_storage

        load_storage = memory_storage.load(initial_state=initial_state)
    else:
        name_prefix = os.getenv("STATE_NAME_PREFIX")
        namespace = os.getenv("STATE_NAMESPACE")

        if not (namespace and name_prefix):
            raise ValueError("Kubernetes state config missing")

        name = f"{name_prefix}{rule.name}"

        load_storage = config_map_storage.load(
            initial_state=initial_state,
            namespace=namespace,
            config_map_name=name,
        )

    return asyncio.run(load_storage)


def _init_rules(config_dir: str) -> List[RuleState]:
    secrets = os.environ
    initialized_rules = [
        rules.DartsRule(config_dir),
        rules.DiceRule(config_dir),
        rules.NhoRule(config_dir),
        rules.SkyRule(config_dir),
        rules.SlashRule(config_dir),
        rules.SmartypantsRule(config_dir, secrets=secrets),  # type: ignore
    ]
    return [RuleState(rule, _load_state_storage(rule)) for rule in initialized_rules]


def _setup_logging():
    logging.basicConfig()
    _LOG.level = logging.DEBUG


def _setup_sentry():
    dsn = os.getenv("SENTRY_DSN")
    if not dsn:
        _LOG.warning("Sentry DSN not found")
        return

    version = os.getenv("BUILD_SHA", "dirty")

    sentry_sdk.init(
        dsn,
        release=version,
    )


def main() -> None:
    _setup_logging()
    _setup_sentry()

    if not telegram.is_configured():
        _LOG.error("Missing API key")
        sys.exit(1)

    if not _CONFIG_DIRECTORY:
        _LOG.warning("CONFIG_DIR is not set")

    args = sys.argv
    if len(args) > 1:
        arg = args[1]

        config_dir = _CONFIG_DIRECTORY or "config"
        handler: EventRule
        if arg == "--subscribe-horoscopes":
            handler = event_rule.IdolRule(config_dir)
        else:
            _LOG.error("Invalid arguments (%s)", args)
            sys.exit(1)

        subscriber = EventSubscriber(
            rule=handler,
        )
        subscriber.subscribe()
    else:
        rule_states = _init_rules(_CONFIG_DIRECTORY or "config")
        _handle_updates(rule_states)


if __name__ == "__main__":
    main()
