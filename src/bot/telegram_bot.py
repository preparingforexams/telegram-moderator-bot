import logging
import signal
from typing import Any

import telegram
from telegram.ext import Application, MessageHandler, filters

from bot.config import Config
from bot.rule_state import RuleState

_LOG = logging.getLogger(__name__)


class TelegramBot:
    def __init__(self, config: Config, rule_states: list[RuleState]) -> None:
        self.config = config
        self.rule_states = rule_states
        self.bot = telegram.Bot(token=config.telegram_token)

    async def run(self) -> None:
        app = Application.builder().bot(self.bot).build()
        app.add_handler(
            MessageHandler(
                filters=filters.ALL,
                callback=self._on_message,
            )
        )

        _LOG.info("Running bot")
        app.run_polling(
            stop_signals=[signal.SIGTERM, signal.SIGINT],
        )
        _LOG.info("run_polling has returned")

    async def _on_message(self, update: telegram.Update, _: Any) -> None:
        message = update.message or update.edited_message
        message_is_edited = update.edited_message is not None

        if message is None:
            _LOG.error("Received non-message update: %s", update.to_json())
            return

        chat_id = message.chat_id

        for rule_state in self.rule_states:
            rule = rule_state.rule
            _LOG.debug("Loading state for rule %s", rule.name())
            state_storage = rule_state.state_storage
            if state_storage is not None:
                state = await state_storage.load()
                old_state = state.model_copy(deep=True)
            else:
                state = None
                old_state = None

            _LOG.debug("Passing message to rule %s", rule.name())
            try:
                await rule(
                    chat_id=chat_id,
                    message=message.to_dict(),
                    is_edited=message_is_edited,
                    state=state,
                )
            except Exception as e:
                _LOG.error("Rule threw an exception", exc_info=e)
            else:
                if state_storage is not None and old_state != state:
                    await state_storage.store(state)
