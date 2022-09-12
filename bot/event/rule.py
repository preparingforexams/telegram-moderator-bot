import abc


class EventRule(abc.ABC):
    @property
    @abc.abstractmethod
    def name(self) -> str:
        pass

    @abc.abstractmethod
    def __call__(self, event: dict) -> bool:
        pass
