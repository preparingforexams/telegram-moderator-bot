from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from pydantic import BaseModel

S = TypeVar("S", bound=BaseModel | None)


class Rule(ABC, Generic[S]):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def initial_state(self) -> S:
        pass

    @abstractmethod
    async def __call__(
        self,
        *,
        chat_id: int,
        message: dict,
        is_edited: bool,
        state: S,
    ) -> None:
        pass
