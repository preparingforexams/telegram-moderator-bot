import logging
import os
import sys
from typing import List

import sentry_sdk

from bot import rule
from bot import telegram

_ADMIN_USER_ID = os.getenv("ADMIN_USER_ID")
_CONFIG_DIRECTORY = os.getenv("CONFIG_DIR")

_LOG = logging.getLogger("bot")


def _handle_updates(rules: List[rule.Rule]) -> None:
    def _on_update(update: dict):
        message = update.get("message")

        if not message:
            _LOG.debug("Skipping non-message update")
            return

        chat_id = message['chat']['id']

        for rule in rules:
            _LOG.debug("Passing message to rule %s", rule.name)
            try:
                rule(chat_id, message)
            except Exception as e:
                _LOG.error("Rule threw an exception", exc_info=e)

    telegram.handle_updates(_on_update)


def _init_rules(config_dir: str) -> List[rule.Rule]:
    return [
        rule.DartsRule(config_dir),
        rule.DiceRule(config_dir),
        rule.NhoRule(config_dir),
        rule.SkyRule(config_dir),
        rule.SlashRule(config_dir),
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

        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        # We recommend adjusting this value in production.
        traces_sample_rate=1.0
    )


def main():
    _setup_logging()
    _setup_sentry()

    if not telegram.is_configured():
        _LOG.error("Missing API key")
        sys.exit(1)

    if not _CONFIG_DIRECTORY:
        _LOG.warning("CONFIG_DIR is not set")

    rules = _init_rules(_CONFIG_DIRECTORY or "config")
    _handle_updates(rules)


if __name__ == '__main__':
    main()
