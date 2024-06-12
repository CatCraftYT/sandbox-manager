from typing import Any, Callable
from classes.category_handlers import CategoryBase, category_handlers

class ConfigParser():
    args: list[str]
    handlers: list[CategoryBase]

    def __init__(self, config: dict[str, Any]):
        if not isinstance(config, dict):
            raise AttributeError(f"Config file has an invalid structure.")

        self.args = []
        self.handlers = []

        # Add config handlers and instantiate with configs
        for category, settings in config.items():
            if category not in category_handlers:
                raise AttributeError(f"'{category}' is not a valid configuration category.")
            self.handlers.append(category_handlers[category](settings))
        
        # Add default args
        for handler in category_handlers.values():
            if type(handler) not in self.handlers:
                self.args += handler.default_args()
    
    def prepare(self) -> list[Callable]:
        callbacks = []

        for handler in self.handlers:
            callback = handler.prepare()
            if callback:
                callbacks += callback
        
        return callbacks

    def to_args(self) -> list[str]:
        for handler in self.handlers:
            self.args += handler.to_args()
        
        return self.args