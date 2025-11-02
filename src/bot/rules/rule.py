from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from telegram import Message


class Rule[S: BaseModel | None](ABC):
    @classmethod
    @abstractmethod
    def name(cls) -> str:
        pass

    @abstractmethod
    def initial_state(self) -> S:
        pass

    @abstractmethod
    async def __call__(
        self,
        *,
        chat_id: int,
        message: Message,
        is_edited: bool,
        state: S,
    ) -> None:
        pass
