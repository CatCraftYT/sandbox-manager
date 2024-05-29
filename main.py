from classes.sandbox import Sandbox
from yaml import safe_load

sandbox = None
with open("examples/base.yaml", "r") as f:
    config = safe_load(f)
    sandbox = Sandbox(config)

sandbox.finalize_perms()
sandbox.run()
