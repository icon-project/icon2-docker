#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import append_parent_path
from common import resources
from devtools import debug

print(f"\n--- System Information ----")
print(resources.get_platform_info())

print(f"\n--- Memory Information ----")
print(f"{resources.get_mem_info()}")

print(f"\n--- rlimit Information ----")
print(resources.get_rlimit_nofile())

print(f"\n--- CPU LOAD Information ----")
print(resources.get_cpu_load())

print(f"\n--- CPU Percentage Information ----")
print(resources.get_cpu_usage_percentage())

print(f"\n--- Memory Information ----")
debug(resources.get_mem_info(unit="GB"))
