from classes.sandbox import Sandbox
from classes.config_loader import ConfigLoader
from yaml import safe_dump
from argparse import ArgumentParser
import sys
import os

argparser = ArgumentParser(
    prog="run-sandbox",
    description="Python script for managing bubblewrap (bwrap) sandboxes.",
    epilog="Configuration files will be read from directories contained within \
    the '--search-in' argument(s), or from the 'SANDBOX_CONFIG_DIRS' environment \
    variable (seperated by colons), in that order. \
    Read the man page for more information on configuration and security."
)
argparser.add_argument(
    "--flatten", "-f",
    action="store_true",
    default=False,
    help="Parse the given configuration file and its dependencies, \
    print out a new configuration file with the dependencies integrated, then exit. \
    Useful for determining exactly what a program will be given access to."
)
argparser.add_argument(
    "--run",
    metavar="EXECUTABLE",
    default=None,
    help="A program to run instead of the one specified in the given config file. \
    Useful for running a shell in your program's environment."
)
argparser.add_argument(
    "--search-in", "-s",
    action="append",
    default=[],
    metavar="DIR",
    help="A directory to search for config files in. Can be specified multiple times."
)
argparser.add_argument(
    "filename",
    help="The name of the configuration file to run, without the file extension."
)

# Path of this script in the filesystem
script_path = os.path.abspath(os.path.dirname(__file__))
args = argparser.parse_args()

search_paths = args.search_in + os.environ.get("SANDBOX_CONFIG_DIRS", "").split(":") + [os.path.join(script_path, "default_configs/")]
# Remove empty strings and lists
search_paths = [i for i in search_paths if i]

config_loader = ConfigLoader(search_paths)
config_loader.load(args.filename)

if args.flatten:
    safe_dump(config_loader.config, sys.stdout)
    sys.exit(0)

sandbox = None
sandbox = Sandbox(config_loader.config, blocking=args.blocking)

if args.run:
    sandbox.executable = args.run

sandbox.run()
