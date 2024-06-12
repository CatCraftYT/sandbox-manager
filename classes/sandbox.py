import warnings
import os
import atexit
import classes.permissions as permissions
from collections.abc import Callable
from typing import Any
from subprocess import Popen
from re import sub


class Sandbox():
    permission_list: list[permissions.BasePermission]
    termination_callbacks: list[Callable]
    app_name: str
    executable: str
    # Args always prepended to bwrap args regardless of config
    constant_args: list[str] = [
        "--new-session",
        "--die-with-parent",
        "--clearenv"
    ]
    # Default bwrap args for sandboxes that don't specify
    # some permission categories (e.g. sharing namespaces).
    default_args: dict[str, str] = {
        "namespaces": "--unshare-all",
    }

    # Config is the output of yaml.safe_load()
    def __init__(self, config: dict[str, Any], blocking: bool = False):
        self.permission_list = []
        self.termination_callbacks = []
        self.app_name = ""
        self.executable = ""
        self.block = blocking

        # Guarantee that the app name env variable will be set regardless
        # of its position in the config (needed for dbus)
        if config.get("name"):
            self._set_app_name(config["name"])
        else:
            warnings.warn("This sandbox has no app name. Some config options (particularly D-Bus) may not work properly.", RuntimeWarning)

        if not isinstance(config, dict):
            raise AttributeError("Invalid config file.")

        for key, value in config.items():
            self._handle_config(key, value)

        if not self.executable:
            raise AttributeError(f"No executable was specified in the given config '{self.app_name}'.")
            
    def _handle_config(self, name: str, value: Any) -> None:
        match name:
            case "name":
                pass
            case "run":
                self.executable = value
            case "preprocess":
                self._handle_preprocessing(value)
            case "permissions":
                self._handle_permissions(value)
            case _:
                raise AttributeError(f"'{value}' is not a valid configuration category.")
    
    def _set_app_name(self, name: str) -> None:
        self.app_name = name
        os.environ["appNameWspace"] = self.app_name
        os.environ["appName"] = sub(r"\s+", "", self.app_name)
        
    def _handle_permissions(self, permission_dict: dict[str, Any]) -> None:
        for key, settings in permission_dict.items():
            new_perm = self._handle_permission_category(key, settings)
            self.permission_list.append(new_perm)

    # Using Any type for settings since namespaces will be a list instead of a dict.
    def _handle_permission_category(self, name: str, settings: Any) -> permissions.BasePermission:
        match name:
            case "filesystem":
                return permissions.FilePermissions(settings)
            case "dbus":
                return permissions.DbusPermissions(settings)
            case "namespaces":
                self.default_args.pop("namespaces")
                return permissions.NamespacePermissions(settings)
            case "environment":
                return permissions.EnvironmentPermissions(settings)
            case _:
                raise AttributeError(f"'{name}' is not a valid permission configuration category.")
    
    def _handle_preprocessing(self, config: dict[str, list[str]]) -> None:
        for operation, value in config.items():
            match operation:
                case "create-dirs":
                    for directory in value:
                        # Permission mode follows umask
                        os.makedirs(os.path.expanduser(os.path.expandvars(directory)), exist_ok=True)
                case _:
                    raise AttributeError(f"'{operation}' is not a valid preprocessing operation.")

    def create_bwrap_command(self) -> str:
        command = "bwrap "

        command += " ".join(self.constant_args)
        command += " ".join(self.default_args.values())
        command += " "

        for permission in self.permission_list:
            command += permission.to_args() + " "
        
        command += "-- " + self.executable
        return command
    
    def _prepare(self) -> None:
        for permission in self.permission_list:
            callback = permission.prepare()
            if callback:
                self.termination_callbacks += callback

    def run(self) -> Popen:
        self._prepare()
        command = self.create_bwrap_command()

        process = Popen(command, shell=True, close_fds=False)

        # Always block and run in background since
        # it's difficult to terminate the sandbox otherwise
        atexit.register(process.terminate)
        process.wait()

        if len(self.termination_callbacks) > 0:
            for callback in self.termination_callbacks:
                callback()
        
        return process
