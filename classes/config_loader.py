import warnings
from typing import Any
from os import walk
from yaml import safe_load
from deepmerge import always_merger as merger


class ConfigLoader():
    search_paths: list[str]
    config: dict[str, Any]

    def __init__(self, search_paths: list[str]):
        self.search_paths = search_paths
        self.config = {}
    
    def load(self, config_name: str) -> dict[str, Any]:
        self.config = self._load(config_name)
        self.config.pop("inherit")
        return self.config

    # Doesn't set self.config and doesn't remove inherits
    def _load(self, config_name: str) -> dict[str, Any]:
        config_file = self.find_file(config_name + ".yaml")
        config = None

        with open(config_file, "r") as file:
            config = safe_load(file)
        
        config = self.merge_inherits(config)
        
        return config

    def merge_inherits(self, config: dict[str, Any]) -> dict[str, Any]:
        inherit_list = config.get("inherit")
        if inherit_list:
            for name in inherit_list:
                inherited_config = self._load(name)
                config = self.merge_config(config, inherited_config)

        return config

    def merge_config(self, config: dict[str, Any], other_config: dict[str, Any]) -> dict[str, Any]:
        new_config = config
        categories = ["permissions", "preprocess", "environment"]
        for key,value in other_config.items():
            if key == "run":
                warnings.warn(f"Inherited config '{other_config}' includes a run statement. It will be ignored. If you wanted to run it, start a seperate sandbox.", RuntimeWarning)
                continue
            
            for category in categories:
                # merger.merge(None, some_dict) will return some_dict
                if key == category:
                    new_config[category] = merger.merge(new_config.get(category), value)
        
        return config
        
    def find_file(self, filename: str) -> str:
        for path in self.search_paths:
            generator = walk(path)
            for directory,_,file_list in generator:
                for file in file_list:
                    if file == filename:
                        return directory + file
        raise FileNotFoundError(f"Could not find config file '{filename}'")
