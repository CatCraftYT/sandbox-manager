from classes.sandbox import Sandbox
from classes.config_loader import ConfigLoader
from yaml import safe_dump
from argparse import ArgumentParser
import sys

argparser = ArgumentParser(
    prog="sandbox",
    description="Python script for managing bubblewrap (bwrap) sandboxes.",
    epilog="Read the man page for more information on configuration and security."
)
argparser.add_argument(
    "--blocking", "-b",
    action="store_true",
    default=False,
    help="If set, the script will wait for the sandbox process to terminate before terminating itself. \
    Useful when running a shell so that it runs in the foreground."
)
argparser.add_argument(
    "--run",
    metavar="EXECUTABLE",
    default=None,
    help="A program to run instead of the one specified in the given config file. \
    Useful for running a shell in your program's environment."
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
    "filename",
    help="The name of the configuration file to run, without the file extension."
)

args = argparser.parse_args()

config_loader = ConfigLoader(["default_configs/"])
config_loader.load("test")

if args.flatten:
    safe_dump(config_loader.config, sys.stdout)
    sys.exit(0)

sandbox = None
sandbox = Sandbox(config_loader.config, blocking=args.blocking)

if args.run:
    sandbox.executable = args.run

sandbox.run()
