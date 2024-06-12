from typing import Any
from classes.category_handlers import CategoryBase, category_handlers

class ConfigHandler():
    args: list[str]
    handlers: list[CategoryBase]

    def __init__(self, config: dict[str, Any]):
        self.args = []
        self.handlers = []

        # Add config handlers and instantiate with configs
        for category, settings in config.items():
            if category not in category_handlers:
                raise AttributeError(f"'{category}' is not a valid configuration category.")
            self.handlers.append(category_handlers[category](settings))
        
        # Add default args
        for handler in category_handlers:
            if type(handler) not in self.handlers:
                self.args += handler.default_args()
    
    def prepare(self):
        callbacks = []

        for handler in self.handlers:
            callback = handler.prepare()
            if callback:
                callbacks.append(callback)
        
        return callbacks

    def to_args(self) -> str:
        for handler in self.handlers:
            self.args += handler.to_args()
        
        return " ".join(self.args)