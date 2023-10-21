import logging
import os
import sys
from dataclasses import dataclass
from typing import Generic, List, TypeVar, Union

import sentry_sdk
from pydantic import BaseModel

from bot import rules, telegram
from bot.events import rules as event_rule
from bot.events.rule import EventRule
from bot.events.subscriber import EventSubscriber

_ADMIN_USER_ID = os.getenv("ADMIN_USER_ID")
_CONFIG_DIRECTORY = os.getenv("CONFIG_DIR")

_LOG = logging.getLogger("bot")

S = TypeVar("S", bound=Union[BaseModel, None])


@dataclass
class RuleState(Generic[S]):
    rule: rules.Rule[S]
    state: S


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
            _LOG.debug("Passing message to rule %s", rule.name)
            try:
                rule(
                    chat_id,
                    effective_message,
                    is_edited=edited_message is not None,
                    state=rule_state.state,
                )
            except Exception as e:
                _LOG.error("Rule threw an exception", exc_info=e)

    telegram.handle_updates(_on_update)


def _load_state(rule: rules.Rule[S]) -> S:
    # TODO: load state
    return rule.initial_state()


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
    return [RuleState(rule, _load_state(rule)) for rule in initialized_rules]


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
