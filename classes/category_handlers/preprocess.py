import os
from classes.category_handlers.category_base import CategoryBase

class PreprocessingHandler(CategoryBase):
    directories: list[str]

    def __init__(self, config: dict[str, list[str]]):
        self.directories = []

        for operation, value in config.items():
            match operation:
                case "create-dirs":
                    for directory in value:
                        self.directories += directory
                case _:
                    raise AttributeError(f"'{operation}' is not a valid preprocessing operation.")

    def prepare(self) -> None:
        for directory in self.directories:
            # Permission mode follows umask
            os.makedirs(os.path.expanduser(os.path.expandvars(directory)), exist_ok=True)

    def to_args(self) -> list[str]:
        return []


handler = PreprocessingHandler
