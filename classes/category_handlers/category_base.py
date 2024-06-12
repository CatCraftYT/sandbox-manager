from abc import ABC, abstractmethod
from typing import Optional, Any
from collections.abc import Callable

# Abstract base class (ABC) for a configuration category.
# All categories must inherit from this.
class CategoryBase(ABC):
    @abstractmethod
    def __init__(self, config: dict[str, Any]):
        pass
    
    # Returns a list containing argument strings to be appended to bwrap.
    # For example: ["--bind / /", "--unshare-all"]
    # Must be implemented.
    @abstractmethod
    def to_args(self) -> list[str]:
        return []

    # Called if the category isn't present within the given config.
    # Provides a list of default arguments to pass to bubblewrap, e.g.
    # ["--unshare-all"]
    @staticmethod
    def default_args() -> list[str]:
        return []
    
    # Called before the sandbox is run.
    # Returns either None, or a list of functions to call
    # after the sandbox terminates
    def prepare(self) -> Optional[list[Callable]]:
        pass
    