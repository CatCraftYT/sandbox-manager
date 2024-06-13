import warnings
from typing import Any
from os import walk
from os.path import join as pathjoin
from yaml import safe_load
from deepmerge import always_merger as merger


class ConfigLoader():
    search_paths: list[str]
    config: dict[str, Any]

    def __init__(self, search_paths: list[str]):
        self.search_paths = search_paths
        self.config = {}
    
    def load(self, config_name: str) -> dict[str, Any]:
        config_file = self.find_file(config_name + ".yaml")
        with open(config_file, "r") as file:
            config: dict[str, Any] = safe_load(file)
        
        config_inherits = config.pop("inherit", None)
        if not config_inherits:
            self.config = config
            return config
        
        inherit_loader = ConfigLoader(self.search_paths)

        inherited_configs: list[dict[str, Any]] = []
        for inherited_name in config_inherits:
            inherit_loader.load(inherited_name)
            inherited_config = inherit_loader.config
            
            # Remove name and run statements
            inherited_config.pop("name", None)
            if inherited_config.pop("run", None):
                warnings.warn(f"Inherited config '{inherited_name}' includes a run statement. It will be ignored. If you wanted to run it, start a seperate sandbox.", RuntimeWarning)
            
            inherited_configs.append(inherited_config)
            inherit_loader.config = {}
        
        self.config = inherited_configs[0]
        # If there's only one inherit then the list will be empty
        for other_config in inherited_configs[1:]:
            # First arg becomes returned value after merge
            merger.merge(self.config, other_config)
        
        return merger.merge(self.config, config)
        
        
    def find_file(self, filename: str) -> str:
        for path in self.search_paths:
            generator = walk(path)
            for directory,_,file_list in generator:
                for file in file_list:
                    if file == filename:
                        return pathjoin(directory, file)
        raise FileNotFoundError(f"Could not find config file '{filename}'")
