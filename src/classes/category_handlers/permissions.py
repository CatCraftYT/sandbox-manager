import os
import atexit
import __main__ as main
from classes.category_handlers.category_base import CategoryBase
from subprocess import Popen
from typing import Any, Optional
from collections.abc import Callable
from abc import ABC, abstractmethod


# Abstract base class (ABC) for a permission.
# All permissions should inherit from this.
class BasePermission(ABC):
    @abstractmethod
    def to_args(self) -> list[str]:
        return ""

    # Not abstract because not every function will need this
    def prepare(self) -> Optional[list[Callable]]:
        pass


class PermissionHandler(CategoryBase):
    permission_list: list[BasePermission]
    defaults: list[str] = [
        "--unshare-all",
    ]

    def __init__(self, config: dict[str, Any]):
        if not isinstance(config, dict):
            raise AttributeError(f"Config category 'permissions' has an invalid structure.")
        
        self.permission_list = []

        for key, settings in config.items():
            new_perm = self.handle_permission_category(key, settings)
            self.permission_list.append(new_perm)
    
    # Using Any type for settings since namespaces will be a list instead of a dict.
    def handle_permission_category(self, name: str, settings: Any) -> BasePermission:
        match name:
            case "filesystem":
                return FilePermissions(settings)
            case "dbus":
                return DbusPermissions(settings)
            case "namespaces":
                self.defaults.remove("--unshare-all")
                return NamespacePermissions(settings)
            case "environment":
                return EnvironmentPermissions(settings)
            case _:
                raise AttributeError(f"'{name}' is not a valid permission configuration category.")

    def prepare(self) -> list[Callable]:
        callbacks = []

        for perm in self.permission_list:
            perm_callbacks = perm.prepare()
            if perm_callbacks:
                callbacks += perm_callbacks
        
        return callbacks

    def to_args(self) -> list[str]:
        args = []

        for permission in self.permission_list:
            args += permission.to_args()
        
        return args
    
    @staticmethod
    def default_args() -> list[str]:
        return PermissionHandler.defaults


handler = PermissionHandler

# /////////////////////////////////////////////////////////////////// #
# Permission categories


class FilePermissions(BasePermission):
    args: list[str]
    tempfiles: list[str]
    arg_templates: dict[str, str | Callable]

    def __init__(self, settings: dict[str, list[str] | dict[str, str]]):
        self.tempfiles = []
        self.args = []
        self.arg_templates = {
            "ro-bind": "--ro-bind {0} {0}",
            "ro-bind-opt": "--ro-bind-try {0} {0}",
            "ro-bind-to": "--ro-bind {0}",
            "ro-bind-to-opt": "--ro-bind-try {0}",
            "bind-devices": "--dev-bind {0} {0}",
            "bind-devices-opt": "--dev-bind-try {0} {0}",
            "bind-devices-to": "--dev-bind {0}",
            "bind-devices-to-opt": "--dev-bind-try {0}",
            "bind": "--bind {0} {0}",
            "bind-opt": "--bind-try {0} {0}",
            "bind-to": "--bind {0}",
            "bind-to-opt": "--bind {0}",
            "link": "--symlink {0}",
            "new-dev": "--dev {0}",
            "new-tmpfs": "--tmpfs {0}",
            "new-proc": "--proc {0}",
            "create-files": self.handle_file_create
        }

        for permission_name, permission in settings.items():
            arg = self.parse_config(permission_name, permission)
            self.args += arg

    def parse_config(self, name: str, args: list[str] | dict[str, str]) -> list[str]:
        handler = self.arg_templates.get(name, None)
        if handler == None:
            raise AttributeError(f"'{name}' is not a valid filesystem permission.")
        
        if isinstance(handler, Callable):
            return handler(args)

        if not isinstance(args, list):
            raise AttributeError(f"'{name}' has an invalid argument. It should be a list.")

        return [handler.format(arg) for arg in args]

    def handle_file_create(self, config: dict[str, str]) -> list[str]:
        import tempfile
        if not isinstance(config, dict):
            raise AttributeError(f"'create-files' needs to be a linked list of the form 'name: data'.")

        if not os.path.exists("/tmp/sandbox_files"):
            os.mkdir("/tmp/sandbox_files")
        
        args = []
        for bind_path, contents in config.items():
            if not isinstance(bind_path, str) or not isinstance(contents, str):
                raise AttributeError(f"'create-files' has an invalid structure.")
            
            file = tempfile.NamedTemporaryFile(mode="w+", dir="/tmp/sandbox_files", prefix=os.environ.get("appName", ""), delete=False)
            file.write(os.path.expanduser(os.path.expandvars(contents)))
            self.tempfiles.append(file.name)
            file.close()

            args.append(f"--ro-bind {file.name} {bind_path}")
        
        atexit.register(self.cleanup_tempfiles)

        return args

    def cleanup_tempfiles(self):
        for file in self.tempfiles:
            os.remove(file)

    def to_args(self) -> list[str]:
        return self.args


class DbusPermissions(BasePermission):
    see_names: list[str]
    talk_names: list[str]
    own_names: list[str]
    proxy_process: Popen

    def __init__(self, settings: dict[str, list[str]]):
        if not isinstance(settings, dict):
            raise AttributeError(f"Permission category 'dbus' has an invalid structure.")
        
        self.see_names = []
        self.talk_names = []
        self.own_names = []

        for permission_name, permission in settings.items():
            self.parse_config(permission_name, permission)
    
    def parse_config(self, name: str, arg: list[str]) -> None:
        if not isinstance(name, str) or not isinstance(arg, list):
            raise AttributeError(f"Permission category 'dbus' has an invalid structure.")
        
        match name:
            case "see":
                self.see_names += arg
                return
            case "talk":
                self.talk_names += arg
                return
            case "own":
                self.own_names += arg
                return
            case _:
                raise AttributeError(f"'{name}' is not a valid dbus permission type.")

    def to_args(self) -> list[str]:
        return ['--setenv DBUS_SESSION_BUS_ADDRESS unix:path="$XDG_RUNTIME_DIR"/bus', '--bind "$XDG_RUNTIME_DIR"/xdg-dbus-proxy/$appName.sock "$XDG_RUNTIME_DIR"/bus']
    
    def close_dbus_proxy(self) -> None:
        self.proxy_process.terminate()
        # Remove the socket so that xdg-dbus-proxy can use it again later
        os.remove(os.path.expandvars("$XDG_RUNTIME_DIR/xdg-dbus-proxy/$appName.sock"))
    
    def prepare(self) -> Optional[list[Callable]]:
        from time import sleep
        from classes.sandbox import Sandbox
        from classes.config_loader import ConfigLoader

        # Using a list because we can't have trailing spaces (it becomes part of the arg)
        args = []
        if self.see_names:
            args.append("--see=" + " --see=".join(self.see_names))
        if self.talk_names:
            args.append("--talk=" + " --talk=".join(self.talk_names))
        if self.own_names:
            args.append("--own=" + " --own=".join(self.own_names))
        args = " ".join(args)

        # For security reasons, we only search for the dbus sandbox file
        # in the directory the sandbox script is located in
        script_path = os.path.dirname(main.__file__)
        config_loader = ConfigLoader([script_path])
        config_loader.load("dbus")
        config_loader.config["name"] = os.environ["appName"]
        config_loader.config["run"] += " " + args
        dbus_sandbox = Sandbox(config_loader.config, blocking=False)

        self.proxy_process = dbus_sandbox.run()

        # Wait for xdg-dbus-proxy to open the socket.
        while not os.path.exists(os.path.expandvars("$XDG_RUNTIME_DIR/xdg-dbus-proxy/$appName.sock")):
            sleep(0.1)

        return [self.close_dbus_proxy]
        

class NamespacePermissions(BasePermission):
    # Using 'unshare-user-try' instead of 'unshare-user' because it makes
    # this method of getting args much easier. However, for transparency's sake,
    # I may want to add a warning if bwrap is unable to unshare.
    # Since bwrap would be unable to unshare user/cgroup anyway, it isn't very bad.
    # It's also the default behaviour of 'unshare-all'.
    types: dict[str, str] = {
        "share-user": "unshare-user-try",
        "share-cgroup": "unshare-cgroup-try",
        "share-ipc": "unshare-ipc",
        "share-pid": "unshare-pid",
        "share-network": "unshare-net",
        "share-hostname": "unshare-uts",
    }
    types_processed: dict[str, str]
    
    def __init__(self, allowed_namespaces: list[str]):
        if not isinstance(allowed_namespaces, list):
            raise AttributeError(f"Permission category 'namespaces' has an invalid structure.")
        
        self.types_processed = self.types.copy()

        for namespace in allowed_namespaces:
            if namespace in self.types.keys():
                self.types_processed.pop(namespace)
            else:
                raise AttributeError(f"'{namespace}' is not a valid namespace permission.")

    def to_args(self) -> list[str]:
        return ["--" + arg for arg in self.types_processed.values()]


class EnvironmentPermissions(BasePermission):
    args: list[str]

    def __init__(self, settings: dict[str, list[str]]):
        if not isinstance(settings, dict):
            raise AttributeError(f"Permission category 'environment' has an invalid structure.")
        
        self.args = []

        for option, variables in settings.items():
            if not isinstance(option, str) or not isinstance(variables, list):
                raise AttributeError(f"Permission category 'environment' has an invalid structure.")
            
            self.args += self.parse_config(option, variables)

    def parse_config(self, option_name: str, variables: list[str]) -> list[str]:
        if not isinstance(option_name, str) or not isinstance(variables, list):
            raise AttributeError(f"Permission category 'environment' has an invalid structure.")
        
        match option_name:
            case "copyenv":
                return [f"--setenv {name} ${name}" for name in variables]
            case "setenv":
                # Split on spaces, set first arg to first word,
                # set other arg to everything else with spaces in between
                return [f"--setenv {name.split(" ")[0]} \"{' '.join(name.split(" ")[1:])}\"" for name in variables]
            case _:
                raise AttributeError(f"'{option_name}' is not a valid environment permission.")

    def to_args(self) -> list[str]:
        return self.args
