from abc import ABC, abstractmethod


class BaseComputer(ABC):
    @property
    @abstractmethod
    def environment(self):
        pass

    @property
    def dimensions(self):
        pass

    @abstractmethod
    async def screenshot(self) -> str:
        pass

    @abstractmethod
    async def click(self, x: int, y: int, button: str = "left") -> None:
        pass

    @abstractmethod
    async def double_click(self, x: int, y: int) -> None:
        pass

    @abstractmethod
    async def scroll(self, x: int, y: int, scroll_x: int, scroll_y: int) -> None:
        pass

    @abstractmethod
    async def type(self, text: str) -> None:
        pass

    @abstractmethod
    async def wait(self, ms: int = 1000) -> None:
        pass

    @abstractmethod
    async def move(self, x: int, y: int) -> None:
        pass

    @abstractmethod
    async def keypress(self, keys: list[str]) -> None:
        pass
    @abstractmethod
    async def drag(self, path: list[tuple[int, int]]) -> None:
        pass