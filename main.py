from classes.sandbox import Sandbox
from classes.config_loader import ConfigLoader
from yaml import safe_dump
import sys

sandbox = None
config_loader = ConfigLoader(["examples/"])
config_loader.load("test")
safe_dump(config_loader.config, sys.stdout)

#sandbox.finalize_perms()
#sandbox.run()
