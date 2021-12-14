#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import append_parent_path
from common import resources
from devtools import debug

print(f"--- System Information ----")
print(resources.get_platform_info())
print(f"--- Memory Information ----")
print(f"{resources.get_mem_info()}")
print(f"--- rlimit Information ----")
print(resources.get_rlimit_nofile())

print(f"--- CPU LOAD Information ----")
print(resources.get_cpu_load())

print(f"--- CPU Percentage Information ----")
print(resources.get_cpu_usage_percentage())

print(f"--- Memory Information ----")
debug(resources.get_mem_info(unit="GB"))
