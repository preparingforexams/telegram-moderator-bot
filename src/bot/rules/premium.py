import logging
from datetime import UTC, datetime, timedelta

import telegram
from bs_config import Env

from bot.rules.rule import Rule

_LOG = logging.getLogger(__name__)


class PremiumRule(Rule):
    @classmethod
    def name(cls) -> str:
        return "premium"

    def __init__(self, env: Env) -> None:
        self._enabled_chats = env.get_int_list("enabled-chats", default=[])

    def initial_state(self) -> None:
        pass

    async def __call__(
        self,
        *,
        chat_id: int,
        message: telegram.Message,
        is_edited: bool,
        state: None,
    ) -> None:
        if chat_id not in self._enabled_chats:
            _LOG.debug("Not enabled in %d", chat_id)
            return

        user = message.from_user
        if user is None:
            _LOG.debug("No user found")
            return

        if user.is_premium:
            _LOG.debug("User has premium: %s", user.id)
            return

        await message.chat.ban_member(
            user_id=user.id,
            revoke_messages=False,
            until_date=datetime.now(tz=UTC) + timedelta(minutes=1),
        )
