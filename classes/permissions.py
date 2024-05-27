from typing import List

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

    def to_arg(self):
        prefix = ""
        if self.readonly:
            prefix = "ro-"
        elif self.device:
            prefix = "dev-"

        return f"--{prefix}bind{'-try' if self.optional else ''} {self.src} {self.dest}"


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
#    def to_arg(self):
#        return "--" + " --".join(self.args)
#