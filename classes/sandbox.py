from typing import Dict, List, Any
from subprocess import Popen
import classes.permissions as permissions


class Sandbox():
    permissions = []
    end_callbacks = []
    app_name: str = ""
    executable: str = ""

    # Config is the output of yaml.safe_load()
    def __init__(self, config: Dict[str, Any]):
        for key, value in config.items():
            self.handle_config(key, value)

    def handle_config(self, name, value):
        match name:
            case "name":
                self.app_name = value
            case "run":
                self.executable = value
            case "preprocess":
                self.handle_preprocessing(value)
            case "permissions":
                self.handle_permissions(value)
            case _:
                raise AttributeError(f"'{value}' is not a valid configuration category.")
                
    def handle_permissions(self, permission_dict):
        for key, settings in permission_dict.items():
            new_perm = self.handle_permission_category(key, settings)
            self.permissions.append(new_perm)

    def handle_permission_category(self, name, settings):
        match name:
            case "filesystem":
                return permissions.FilePermissions(settings)
            case "dbus":
                return permissions.DbusPermissions(settings)
            case "namespaces":
                return []
                #return permissions.NamespacePermissions(settings)
            case "environment":
                return []
    
    def handle_preprocessing(self, config):
        pass

    def create_bwrap_command(self):
        if not self.executable:
            raise AttributeError(f"No executable was specified in the given config '{self.app_name}'.")
        if not self.app_name:
            raise RuntimeWarning("This sandbox has no app name. Some config options may not work properly.")

        command = "bwrap "
        for permission in self.permissions:
            command += permission.to_args() + " "
        
        command += "-- " + self.executable
        return command
    
    def finalize_perms(self):
        for permission in self.permissions:
            callback = permission.finalize()
            if callback:
                self.end_callbacks += callback

    def run(self):
        command = self.create_bwrap_command()
        print(command)

        if len(self.end_callbacks) > 0:
            #process.wait()
            for callback in self.end_callbacks:
                callback()