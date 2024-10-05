from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from pydantic import BaseModel
from telegram import Message

S = TypeVar("S", bound=BaseModel | None)


class Rule(ABC, Generic[S]):
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
