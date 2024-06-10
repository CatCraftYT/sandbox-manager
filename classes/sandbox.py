import warnings
import os
import classes.permissions as permissions
from collections.abc import Callable
from typing import Any
from subprocess import Popen
from re import sub


class Sandbox():
    permission_list: list[permissions.BasePermission]
    end_callbacks: list[Callable]
    app_name: str
    executable: str

    # Config is the output of yaml.safe_load()
    def __init__(self, config: dict[str, Any]):
        self.permission_list = []
        self.end_callbacks = []
        self.app_name = ""
        self.executable = ""

        for key, value in config.items():
            self._handle_config(key, value)

        if not self.executable:
            raise AttributeError(f"No executable was specified in the given config '{self.app_name}'.")
        if not self.app_name:
            warnings.warn("This sandbox has no app name. Some config options may not work properly.", RuntimeWarning)
            
    def _handle_config(self, name: str, value: Any) -> None:
        match name:
            case "name":
                self._set_app_name(value)
            case "run":
                self.executable = value
            case "preprocess":
                self._handle_preprocessing(value)
            case "permissions":
                self._handle_permissions(value)
            case "environment":
                # Handle environment args
                pass
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

    def _handle_permission_category(self, name: str, settings: dict[str, Any]) -> permissions.BasePermission:
        match name:
            case "filesystem":
                return permissions.FilePermissions(settings)
            case "dbus":
                return permissions.DbusPermissions(settings)
            case "namespaces":
                #return permissions.NamespacePermissions(settings)
                raise NotImplementedError
            case "environment":
                raise NotImplementedError
            case _:
                raise AttributeError(f"'{name}' is not a valid permission configuration category.")
    
    def _handle_preprocessing(self, config: dict[str, str]) -> None:
        raise NotImplementedError

    def create_bwrap_command(self) -> str:
        command = "bwrap "
        for permission in self.permission_list:
            command += permission.to_args() + " "
        
        command += "-- " + self.executable
        return command
    
    def _prepare(self) -> None:
        for permission in self.permission_list:
            callback = permission.prepare()
            if callback:
                self.end_callbacks += callback

    def run(self) -> Popen:
        self._prepare()
        command = self.create_bwrap_command()
        print(command)

        process = Popen(command, shell=True, close_fds=False)

        if len(self.end_callbacks) > 0:
            process.wait()
            for callback in self.end_callbacks:
                callback()
        
        return process