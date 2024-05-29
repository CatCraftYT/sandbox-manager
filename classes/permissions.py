from typing import List, Dict, Tuple
from subprocess import Popen

# Permissions must define these functions:
# - to_args() which returns the bwrap arguments corresponding to its permissions
#
# - finalize() which does any needed work before running the sandbox. The function may simply pass,
#   return nothing, or return a callback to execute after the sandbox ends.

class FilePermissions():
    # Tuple is (argname, bind-from, bind-to)
    args: List[str]

    def __init__(self, settings: Dict[str, str]):
        for permission_name, permission in settings.items():
            self.args.append(self.parse_config(permission_name, permission))

    def parse_config(self, name: str, arg: str) -> str:
        # A little messy :(
        match name:
            case "ro-bind":
                return f"--ro-bind {arg} {arg}"
            case "ro-bind-opt":
                return f"--ro-bind-try {arg} {arg}"
            case "ro-bind-to":
                return f"--ro-bind {arg}"
            case "ro-bind-to-opt":
                return f"--ro-bind-try {arg}"
            case "dev-bind":
                return f"--dev-bind {arg} {arg}"
            case "dev-bind-opt":
                return f"--dev-bind-try {arg} {arg}"
            case "dev-bind-to":
                return f"--dev-bind {arg}"
            case "dev-bind-to-opt":
                return f"--dev-bind-try {arg}"
            case "bind":
                return f"--bind {arg} {arg}"
            case "bind-to":
                return f"--bind {arg}"
            case "bind-opt":
                return f"--bind-try {arg} {arg}"
            case "bind-to-opt":
                return f"--bind-try {arg}"
            case _:
                raise AttributeError(f"'{name}' is not a valid filesystem permission.")

    def to_args(self) -> str:
        return " ".join(self.args)
    
    def finalize(self):
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
                self.see_names.append(arg)
                return
            case "talk":
                self.talk_names.append(arg)
                return
            case "own":
                self.own_names.append(arg)
                return
            case _:
                raise AttributeError(f"'{name}' is not a valid dbus permission type.")

    def to_args(self) -> str:
        return '--setenv DBUS_SESSION_BUS_ADDRESS unix:path="$XDG_RUNTIME_DIR"/bus ' + \
               '--bind "$XDG_RUNTIME_DIR"/xdg-dbus-proxy/$appName.sock "$XDG_RUNTIME_DIR"/bus'
    
    def close_dbus_proxy(self):
        self.proxy_process.terminate()
    
    def finalize(self):
        args = "--see " + " --see ".join(self.see_names) + " " \
               "--talk " + " --talk ".join(self.talk_names) + " " \
               "--own " + " --own ".join(self.own_names)

        # Bodgy, might need to come back to this if I want to generalize to other systems
        # Maybe create a sandbox config file to do it
        self.proxy_process = Popen(['bwrap',
        '--new-session',
        '--die-with-parent',
        '--ro-bind /usr /usr',
        '--bind "$XDG_RUNTIME_DIR/bus" "$XDG_RUNTIME_DIR/bus"',
        '--bind "$XDG_RUNTIME_DIR/xdg-dbus-proxy" "$XDG_RUNTIME_DIR/xdg-dbus-proxy"',
        '--symlink /usr/bin /bin',
        '--symlink /usr/lib /lib',
        '--symlink /usr/lib /lib64',
        '--symlink /usr/bin /sbin',
        '--ro-bind ~/sandboxes/.flatpak-info /.flatpak-info',
        '--ro-bind ~/sandboxes/.flatpak-info "$XDG_RUNTIME_DIR/flatpak-info"',
        '--',
        'xdg-dbus-proxy "$DBUS_SESSION_BUS_ADDRESS" $XDG_RUNTIME_DIR/xdg-dbus-proxy/$appName-proxy.sock --filter',
        args
        ], shell=True)

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