import warnings
import os
import atexit
from classes.config_parser import ConfigParser
from collections.abc import Callable
from typing import Any
from subprocess import Popen
from re import sub


class Sandbox():
    blocking: bool
    config_parser: ConfigParser
    termination_callbacks: list[Callable]
    app_name: str
    executable: str
    # Args always prepended to bwrap args regardless of config
    constant_args: list[str] = [
        "--new-session",
        "--die-with-parent",
        "--clearenv"
    ]

    # Config is the output of yaml.safe_load()
    def __init__(self, config: dict[str, Any], blocking: bool = True):
        self.blocking = blocking
        self.termination_callbacks = []
        self.app_name = ""
        self.executable = ""

        # Guarantee that the app name env variable will be set regardless
        # of its position in the config (needed for dbus)
        if config.get("name"):
            self._set_app_name(config.pop("name"))
        else:
            warnings.warn("This sandbox has no app name. Some config options (particularly D-Bus) may not work properly.", RuntimeWarning)

        if config.get("run"):
            self.executable = config.pop("run")
        else:
            raise AttributeError(f"No executable was specified in the given config '{self.app_name}'.")

        if not isinstance(config, dict):
            raise AttributeError("Invalid config file.")

        self.config_parser = ConfigParser(config)
    
    def _set_app_name(self, name: str) -> None:
        self.app_name = name
        os.environ["appNameWspace"] = self.app_name
        os.environ["appName"] = sub(r"\s+", "", self.app_name)

    def create_bwrap_command(self) -> str:
        command = ["bwrap"]
        command += self.constant_args
        command += self.config_parser.to_args()
        command.append(self.executable)

        return " ".join(command)
    
    def _prepare(self) -> None:
        self.termination_callbacks += self.config_parser.prepare()

    def run(self) -> Popen:
        self._prepare()
        command = self.create_bwrap_command()

        process = Popen(command, shell=True, close_fds=False)
        
        # Always block and run in background since
        # it's difficult to terminate the sandbox otherwise
        if self.blocking:
            atexit.register(process.terminate)
            process.wait()
        
        if len(self.termination_callbacks) > 0:
            for callback in self.termination_callbacks:
                callback()
        
        return process
