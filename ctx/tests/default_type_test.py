#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os

import append_parent_path

from config.configure import Configure
from common import converter, output, base
from common.output import cprint, converter

from devtools import debug


dict_values = dict(
    none_value=None,
    int_value="111",
    float_value=1.11,
    empty_value="",
)


def dict_clean(items):
    result = {}
    for key, value in items:
        if value is None:
            value = 'default'
        result[key] = value
    return result


def set_default_value(value=None, default_value=None):
    if value is None:
        return default_value
    else:
        return dict.get(value)


class GetDict(dict):
    def __init__(self, value):
        self.value = value
        super().__init__()

    # def get(self, item, default_value):
    #     # print(item, default_value)
    #     if item is None:
    #         return default_value
    #     else:
    #         print(dict)
    #         print(self.value.get(item))
    #         return item

    # def __getattr__(self, item):
    #
    #     if super().__getitem__(item) is None:
    #         print(item)
    #
    #     return super().__getitem__(item)
    #
    # def __setattr__(self, item, value):
    #     return super().__setitem__(item, value)


aaa = GetDict(dict_values)

for key, value in dict_values.items():
    print(f"key = {key} , value = {GetDict(dict_values).get(key, 'default')}")

print("-"*100)
print("UpdateType")


class UpdateType:
    def __init__(self, defines=None):
        self.defines = defines

    def run(self):
        for key, value in self.defines.items():

            result = self.check_value_type(key, value)
            print(key, value, result)
        pass

    def str2bool(v):
        true_list = ("yes", "true", "t", "1", "True", "TRUE")
        if type(v) == bool:
            return v
        if type(v) == str:
            return v.lower() in true_list
        return eval(f"{v}") in true_list

    def check_value_type(self, key, value):
        if self.defines.get(key) == "str":
            return_value = str(value)
        elif self.defines.get(key) == "int":
            return_value = int(value)
        elif self.defines.get(key) == "float":
            return_value = float(value)
        elif self.defines.get(key) == "bool":
            return_value = self.str2bool(value)
        elif self.defines.get(key) == "array":
            return_value = str(value).split(",")
        elif self.defines.get(key) == "list":
            return_value = str(value).split(",")
        else:
            return_value = value
        return return_value


default_arguments_type = {
    "hostname": {
        "type": "test_machine",
        "default": "20.20.3.70",
    },
    "default__timeout": {
        "type": "int",
        "default": 3
    },
    "default__db_type": {
        "type": "string",
        "default": "influxdb_v2",
    },
}


default_set = {
    "hostname": "string",
    "integer":  "int",
    "float":  "float",
    "boolean":  "boolean",
    "array": "arr1,arr2,arr3"
}


UpdateType(defines=default_set).run()


