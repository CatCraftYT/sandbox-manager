import warnings
from typing import Any, List, Dict
from os import walk
from yaml import safe_load
from deepmerge import always_merger as merger


class ConfigLoader():
    search_paths: List[str]
    config: Dict[str, Any]

    def __init__(self, search_paths):
        self.search_paths = search_paths
        self.config = {}
    
    def load(self, config_name):
        self.config = self._load(config_name)
        self.config.pop("inherit")
        return self.config

    # Doesn't set self.config and doesn't remove inherits
    def _load(self, config_name):
        config_file = self.find_file(config_name + ".yaml")
        config = None

        with open(config_file, "r") as file:
            config = safe_load(file)
        
        self.merge_inherits(config)
        
        return config

    def merge_inherits(self, config):
        inherit_list = config.get("inherit")
        if inherit_list:
            for name in inherit_list:
                inherited_config = self._load(name)
                config = self.merge_config(config, inherited_config)

        return config

    def merge_config(self, config: Dict[str, Any], other_config: Dict[str, Any]):
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
        
    def find_file(self, filename):
        for path in self.search_paths:
            generator = walk(path)
            for directory,_,file_list in generator:
                for file in file_list:
                    if file == filename:
                        return directory + file
        raise FileNotFoundError(f"Could not find config file '{filename}'")
