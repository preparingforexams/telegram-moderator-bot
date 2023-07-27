import logging
import os
import sys
from typing import List

import sentry_sdk

from bot import rule, telegram
from bot.event import rules as event_rule
from bot.event.rule import EventRule
from bot.event.subscriber import EventSubscriber

_ADMIN_USER_ID = os.getenv("ADMIN_USER_ID")
_CONFIG_DIRECTORY = os.getenv("CONFIG_DIR")

_LOG = logging.getLogger("bot")


def _handle_updates(rules: List[rule.Rule]) -> None:
    def _on_update(update: dict):
        message = update.get("message")
        edited_message = update.get("edited_message")

        if not (message or edited_message):
            _LOG.debug("Skipping non-message update")
            return

        effective_message: dict = message or edited_message  # type: ignore
        chat_id = effective_message["chat"]["id"]

        for rule in rules:
            _LOG.debug("Passing message to rule %s", rule.name)
            try:
                rule(chat_id, effective_message, is_edited=edited_message is not None)
            except Exception as e:
                _LOG.error("Rule threw an exception", exc_info=e)

    telegram.handle_updates(_on_update)


def _init_rules(config_dir: str) -> List[rule.Rule]:
    secrets = os.environ
    return [
        rule.DartsRule(config_dir),
        rule.DiceRule(config_dir),
        rule.NhoRule(config_dir),
        rule.SkyRule(config_dir),
        rule.SlashRule(config_dir),
        rule.SmartypantsRule(config_dir, secrets=secrets),  # type: ignore
    ]


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
        rules = _init_rules(_CONFIG_DIRECTORY or "config")
        _handle_updates(rules)


if __name__ == "__main__":
    main()
