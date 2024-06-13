import os
from classes.category_handlers.category_base import CategoryBase

class PreprocessingHandler(CategoryBase):
    directories: list[str]

    def __init__(self, config: dict[str, list[str]]):
        if not isinstance(config, dict):
            raise AttributeError(f"Config category 'preprocess' has an invalid structure.")
        
        self.directories = []

        for operation, value in config.items():
            if not isinstance(value, list):
                raise AttributeError(f"Config category 'preprocess' has an invalid structure.")
            
            match operation:
                case "create-dirs":
                    for directory in value:
                        if not isinstance(directory, str):
                            raise AttributeError(f"Config category 'preprocess' has an invalid structure.")
                        self.directories.append(directory)
                case _:
                    raise AttributeError(f"'{operation}' is not a valid preprocessing operation.")

    def prepare(self) -> None:
        for directory in self.directories:
            # Permission mode follows umask
            os.makedirs(os.path.expanduser(os.path.expandvars(directory)), exist_ok=True)

    def to_args(self) -> list[str]:
        return []


handler = PreprocessingHandler
