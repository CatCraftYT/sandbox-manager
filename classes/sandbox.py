from typing import Dict, List, Any
import permissions


class Sandbox():
    permissions: List[Any] = []

    # Config is the output of yaml.safe_load()
    def __init__(self, config: Dict[str, Any]):
        for key, settings in config.items():
            new_perm = self.handle_permissions(key, settings)
            self.permissions.append(new_perm)

    def handle_permissions(self, name, settings):
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

    def create_bwrap_command(self):
        return ""