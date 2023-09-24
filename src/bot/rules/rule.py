from abc import ABC, abstractmethod


class Rule(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def __call__(self, chat_id: int, message: dict, is_edited: bool) -> None:
        pass
