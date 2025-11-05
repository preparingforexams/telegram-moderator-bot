import logging
from typing import TYPE_CHECKING

from bot.rules.rule import Rule

if TYPE_CHECKING:
    import telegram
    from bs_config import Env

_LOG = logging.getLogger(__name__)


class LemonRule(Rule):
    @classmethod
    def name(cls) -> str:
        return "lemons"

    def __init__(self, env: Env):
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
            return
        _LOG.debug("Enabled in chat %d", chat_id)

        if (dice := message.dice) and dice.emoji == "🎰":
            dice_value = dice.value

            # 43 is lemon, lemon, lemon
            if dice_value != 43:
                return

            _LOG.info("Found matching message")
            await message.reply_photo(
                photo="AgACAgIAAxkBAANCZubaqbSkbSosatNb5P1AMlLE1uEAAhe1MRsINDlJu4Nokvml5S8BAAMCAAN4AAM2BA",
            )
