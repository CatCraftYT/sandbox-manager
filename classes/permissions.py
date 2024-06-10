import os
import atexit
from subprocess import Popen
from tempfile import _TemporaryFileWrapper
from typing import Any, Optional
from collections.abc import Callable
from abc import ABC, abstractmethod

# Abstract base class (ABC) for a permission.
# All permissions should inherit from this.
class BasePermission(ABC):
    @abstractmethod
    def to_args(self) -> str:
        return ""

    # Not abstract because not every function will need this
    def prepare(self) -> Optional[list[Callable]]:
        pass


class FilePermissions(BasePermission):
    args: list[str]
    # This is needed to keep the temporary files in scope
    # so that the file descriptors remain open for bwrap. Gross.
    tempfiles: list[_TemporaryFileWrapper]

    def __init__(self, settings: dict[str, list[str] | dict[str, str]]):
        self.tempfiles = []
        self.args = []

        for permission_name, permission in settings.items():
            arg = self.parse_config(permission_name, permission)
            self.args += arg

    # Very messy :( :(
    def parse_config(self, name: str, args: list[str] | dict[str, str]) -> list[str]:
        def process_arg_list_double(arg):
            return [f"{arg} {param} {param}" for param in args]
        
        def process_arg_list_single(arg):
            return [f"{arg} {param}" for param in args]

        match name:
            case "ro-bind":
                return process_arg_list_double("--ro-bind")
            case "ro-bind-opt":
                return process_arg_list_double("--ro-bind-try")
            case "ro-bind-to":
                return process_arg_list_single("--ro-bind")
            case "ro-bind-to-opt":
                return process_arg_list_single("--ro-bind-try")
            case "bind-devices":
                return process_arg_list_double("--dev-bind")
            case "bind-devices-opt":
                return process_arg_list_double("--dev-bind-try")
            case "bind-devices-to":
                return process_arg_list_single("--dev-bind")
            case "bind-devices-to-opt":
                return process_arg_list_single("--dev-bind-try")
            case "bind":
                return process_arg_list_double("--bind")
            case "bind-opt":
                return process_arg_list_double("--bind-try")
            case "bind-to":
                return process_arg_list_single("--bind")
            case "bind-to-opt":
                return process_arg_list_single("--bind-try")
            case "link":
                return process_arg_list_single("--symlink")
            case "new-dev":
                return process_arg_list_single("--dev")
            case "new-tmpfs":
                return process_arg_list_single("--tmpfs")
            case "new-proc":
                return process_arg_list_single("--proc")
            case "create-files":
                if not isinstance(args, dict):
                    raise AttributeError(f"'create-files' needs to be a linked list of the form 'name: data'.")

                return self.handle_file_create(args)
            case _:
                raise AttributeError(f"'{name}' is not a valid filesystem permission.")

    def handle_file_create(self, config: dict[str, str]) -> list[str]:
        import tempfile

        args = []
        for bind_path, contents in config.items():
            file = tempfile.NamedTemporaryFile(mode="w+")
            file.write(os.path.expanduser(os.path.expandvars(contents)))
            os.set_inheritable(file.fileno(), True)
            self.tempfiles.append(file)

            # Instruct bwrap to copy from the temporary file (using its file descriptor)
            args.append(f"--bind-data {file.fileno()} {bind_path}")
        
        return args

    def to_args(self) -> str:
        return " ".join(self.args)


class DbusPermissions(BasePermission):
    see_names: list[str]
    talk_names: list[str]
    own_names: list[str]
    proxy_process: Popen

    def __init__(self, settings: dict[str, str]):
        self.see_names = []
        self.talk_names = []
        self.own_names = []

        for permission_name, permission in settings.items():
            self.parse_config(permission_name, permission)
    
    def parse_config(self, name: str, arg: str) -> None:
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

    def to_args(self) -> str:
        return '--setenv DBUS_SESSION_BUS_ADDRESS unix:path="$XDG_RUNTIME_DIR"/bus ' + \
               '--bind "$XDG_RUNTIME_DIR"/xdg-dbus-proxy/$appName.sock "$XDG_RUNTIME_DIR"/bus'
    
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

        # Args to xdg-dbus-proxy set in this environment variable.
        # Since we set them and immediately process the sandbox,
        # it *should* be resistant to an attacker setting the variable.
        os.environ["xdgDbusProxyArgs"] = args

        # For security reasons, we only search for the dbus sandbox file
        # in the directory the sandbox script is located in
        # Get the parent of the script (since this will be located in main/classes)
        script_path = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
        config_loader = ConfigLoader([script_path])
        config_loader.load("dbus")
        config_loader.config["name"] = os.environ["appName"]
        dbus_sandbox = Sandbox(config_loader.config)

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
        self.types_processed = self.types.copy()

        for namespace in allowed_namespaces:
            if namespace in self.types.keys():
                self.types_processed.pop(namespace)
            else:
                raise AttributeError(f"'{namespace}' is not a valid namespace permission.")

    def to_args(self) -> str:
        return "--" + " --".join(self.types.values())


class EnvironmentPermissions(BasePermission):
    args: list[str]

    def __init__(self, settings: dict[str, list[str]]):
        self.args = []

        for option, variables in settings.items():
            self.args += self.parse_config(option, variables)

    def parse_config(self, option_name: str, variables: list[str]) -> list[str]:
        match option_name:
            case "copyenv":
                return [f"--setenv {name} ${name}" for name in variables]
            case "setenv":
                # Split on spaces, set first arg to first word,
                # set other arg to everything else with spaces in between
                return [f"--setenv {name.split(" ")[0]} \"{' '.join(name.split(" ")[1:])}\"" for name in variables]
            case _:
                raise AttributeError(f"'{option_name}' is not a valid environment permission.")

    def to_args(self) -> str:
        return " ".join(self.args)
