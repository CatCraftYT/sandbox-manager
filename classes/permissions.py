import os
from typing import List, Dict, Tuple, Any
from subprocess import Popen

# Permissions must define these functions:
# - to_args() which returns the bwrap arguments corresponding to its permissions
#
# - finalize() which does any needed work before running the sandbox. The function may simply pass,
#   return nothing, or return a callback to execute after the sandbox ends.

class FilePermissions():
    # Tuple is (argname, bind-from, bind-to)
    args: List[str] = []

    def __init__(self, settings: Dict[str, str]):
        for permission_name, permission in settings.items():
            arg = self.parse_config(permission_name, permission)
            self.args += arg

    def parse_config(self, name: str, arg: Any) -> List[str]:
        # A little messy :(
        match name:
            case "ro-bind":
                return [f"--ro-bind {arg} {arg}"]
            case "ro-bind-opt":
                return [f"--ro-bind-try {arg} {arg}"]
            case "ro-bind-to":
                return [f"--ro-bind {arg}"]
            case "ro-bind-to-opt":
                return [f"--ro-bind-try {arg}"]
            case "dev-bind":
                return [f"--dev-bind {arg} {arg}"]
            case "dev-bind-opt":
                return [f"--dev-bind-try {arg} {arg}"]
            case "dev-bind-to":
                return [f"--dev-bind {arg}"]
            case "dev-bind-to-opt":
                return [f"--dev-bind-try {arg}"]
            case "bind":
                return [f"--bind {arg} {arg}"]
            case "bind-to":
                return [f"--bind {arg}"]
            case "bind-opt":
                return [f"--bind-try {arg} {arg}"]
            case "bind-to-opt":
                return [f"--bind-try {arg}"]
            case "link":
                return [f"--symlink {arg}"]
            case "new-dev":
                return [f"--dev {arg}"]
            case "new-tmpfs":
                return [f"--tmpfs {arg}"]
            case "new-proc":
                return [f"--proc {arg}"]
            case "create-files":
                return self.handle_file_create(arg)
            case _:
                raise AttributeError(f"'{name}' is not a valid filesystem permission.")

    # TODO: This will leave a temporary file behind when the sandbox finishes.
    # Unfortunately, I can't create a callback to delete at the end like dbus,
    # since I need this to not block execution when running (because of the dbus sandbox)
    def handle_file_create(self, config: Dict[str, str]) -> List[str]:
        import tempfile

        args = []
        for bind_path, contents in config.items():
            file = tempfile.NamedTemporaryFile(mode="w", delete=False)
            file.write(os.path.expandvars(contents))
            args.append(f"--bind \"{file.name}\", {bind_path}")
        
        return args

    def to_args(self) -> str:
        return " ".join(self.args)
    
    def prepare(self):
        pass


class DbusPermissions():
    see_names: List[str]
    talk_names: List[str]
    own_names: List[str]
    proxy_process: Popen

    def __init__(self, settings: Dict[str, str]):
        for permission_name, permission in settings.items():
            self.parse_config(permission_name, permission)
    
    def parse_config(self, name: str, arg: str):
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
    
    def close_dbus_proxy(self):
        self.proxy_process.terminate()
    
    def prepare(self):
        from classes.sandbox import Sandbox
        from classes.config_loader import ConfigLoader

        args = "--see " + " --see ".join(self.see_names) + " " \
               "--talk " + " --talk ".join(self.talk_names) + " " \
               "--own " + " --own ".join(self.own_names)

        # For security reasons, we only search for the dbus sandbox file
        # in the directory the sandbox script is located in
        script_path = os.path.abspath(os.path.dirname(__file__))
        config_loader = ConfigLoader([script_path])
        dbus_sandbox = Sandbox(config_loader.config)

        dbus_sandbox.prepare()
        self.proxy_process = dbus_sandbox.run()

        return [self.close_dbus_proxy]
        

#class NamespacePermissions():
#    types = {
#        "user": "unshare-user-try",
#        "cgroup": "unshare-cgroup-try",
#        "user-optional": "unshare-user",
#        "cgroup-optional": "unshare-cgroup",
#        "ipc": "unshare-ipc",
#        "pid": "unshare-pid",
#        "net": "unshare-net",
#        "hostname": "unshare-uts",
#    }
#    allowed_namespaces: List[str]
#    args: List[str]
#    
#    def __init__(self, allowed_namespaces):
#        for namespace in allowed_namespaces:
#            if (namespace not in self.types):
#                return AttributeError(f"Namespace name '{namespace}' does not exist.")
#        
#        self.args = [v for k,v in self.types.items() if k not in allowed_namespaces]
#
#    def to_args(self) -> str:
#        return "--" + " --".join(self.args)
#