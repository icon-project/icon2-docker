#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os

parent_dir = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
sys.path.append(parent_dir)
sys.path.append(parent_dir + "/..")

from config.configure import Configure
from common import converter, output, base
from common.output import cprint, converter
from manager import backup

from devtools import debug


def hook_print(*args, **kwargs):
    """
    Print to output every 10th line
    :param args:
    :param kwargs:
    :return:
    """
    if "amplify" in kwargs.get("line"):
        print(f"[output hook - matching keyword] {args} {kwargs}")

    if kwargs.get("line_no") % 1000 == 0:
        print(f"[output hook - matching line_no] {args} {kwargs}")


# Success running
cprint("## Execution error", "yellow")
debug(base.run_execute("ls sdsd ", capture_output=False))

print("")
print("")

# Success running with return stdout
cprint("## Success running", "yellow")
debug(base.run_execute("ls -al ", capture_output=True))

print("")
print("")

# Success running with return stdout and hook_print
cprint("## Success running with hook_print", "yellow")
debug(base.run_execute("find / ", capture_output=False, hook_function=hook_print))

print("")
print("")


# # Success running with change the directory and hook_print
cprint("# Success running with change the directory and hook_print", "yellow")
with base.cd(".."):
    debug(base.run_execute("ls -al", capture_output=False, hook_function=hook_print))

print("")
print("")

# Success running with change the directory and hook_print
cprint("Success running with change the directory and hook_print", "yellow")
debug(base.run_execute("ls -al", capture_output=True, cwd="sdsd", hook_function=hook_print))

print("")
print("")

cprint("Long execution time and throws an error when changing correctly directories", "yellow")
# Long execution time and throws an error when changing correctly directories
with base.cd(".."):
    debug(base.run_execute("find /", capture_output=False, hook_function=hook_print))


cprint("Long execution time and throws an error when changing wrong directories", "yellow")
# Long execution time and throws an error when changing wrong directories
with base.cd("dsfdfdf"):
    debug(base.run_execute("find /", capture_output=False, hook_function=hook_print))


print("")
print("")

cprint("Long execution time and changing correctly directories", "yellow")
# Long execution time and changing correctly directories
with base.cd(".."):
    debug(base.run_execute("find /", capture_output=False, hook_function=hook_print))

