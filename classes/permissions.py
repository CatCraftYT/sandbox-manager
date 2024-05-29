from typing import List
from subprocess import Popen

# Permissions must define these functions:
# - to_args() which returns the bwrap arguments corresponding to its permissions
#
# - finalize() which does any needed work before running the sandbox. The function may simply pass,
#   return nothing, or return a list of processes to terminate after the main sandbox ends.
#   If this function returns anything, then the main script will wait for the sandbox to terminate.

class FilePermission():
    src: str
    dest: str
    readonly: bool
    optional: bool
    device: bool
    
    def __init__(self, src: str, dest: str, readonly: bool, optional: bool, device: bool):
        if (readonly and device):
            return AttributeError("Cannot bind device file as readonly.")

        self.src = src
        self.dest = dest
        self.readonly = readonly
        self.optional = optional
        self.device = device

    def to_args(self) -> str:
        prefix = ""
        if self.readonly:
            prefix = "ro-"
        elif self.device:
            prefix = "dev-"

        return f"--{prefix}bind{'-try' if self.optional else ''} {self.src} {self.dest}"
    
    def finalize(self):
        pass


class DbusPermissions():
    see_names: List[str]
    talk_names: List[str]
    own_names: List[str]

    def __init__(self, see_names, talk_names, own_names):
        self.see_names = see_names
        self.talk_names = talk_names
        self.own_names = own_names
    
    def to_args(self) -> str:
        return '--setenv DBUS_SESSION_BUS_ADDRESS unix:path="$XDG_RUNTIME_DIR"/bus ' + \
               '--bind "$XDG_RUNTIME_DIR"/xdg-dbus-proxy/$appName.sock "$XDG_RUNTIME_DIR"/bus'
    
    def finalize(self):
        args = "--see " + " --see ".join(self.see_names) + " " \
               "--talk " + " --talk ".join(self.see_names) + " " \
               "--own " + " --own ".join(self.see_names)

        # Bodgy, might need to come back to this if I want to generalize to other systems
        return [Popen(['bwrap',
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
        'xdg-dbus-proxy "$DBUS_SESSION_BUS_ADDRESS" $XDG_RUNTIME_DIR/xdg-dbus-proxy/$appName-main-instance.sock --filter',
        args
        ], shell=True)]
        

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