#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os
import append_parent_path
import yaml

from common import converter
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


def check_func(update_type, values, required_type, key=None):
    print(f"\n####### {required_type} Test #######")
    for value in values:
        res = update_type.check_value_type(value, required_type, key)
        print(f"input = {value:<8}, result = {res}")


print(f"----- Not allow None test -----")
for key, value in dict_values.items():
    print(f"key = {key} , value = {GetDict(dict_values).get(key, 'default')}")


print(f"----- UpdateType test -----")
with open('default_configure.yml') as f:
    conf = yaml.load(f, Loader=yaml.FullLoader)
    update_type = converter.UpdateType(config=conf)
    check_func(update_type=update_type, values=['yes', 'true', 't', 'y', '1', 'True', 'TRUE', True], required_type="bool")
    check_func(update_type=update_type, values=['no', 'false', 'f', 'n', '0', 'False', 'FALSE', False], required_type="bool")
    check_func(
        update_type=update_type,
        values=["http://www.com", "http://dsdsd.com", "http://222.222.2.2:23223", "sdsd:2223", "www.hsdsd.com"],
        required_type="url",
        key="URL"
    )

    check_func(
        update_type=update_type,
        values=["202.10.1.1", "0.0.0.0", "422.222.2.2:23223", ":2223", ":dfd", ":sdsd:sdsds", "sdsd,2323", "222.222.2:2222"],
        required_type="port"
    )

    check_func(
        update_type=update_type,
        values=["202.10.1.1", "0.0.0.0", "222.222.2.2:23223", ":2223", "localhost:123", "dssd.com:2323", "aaaa:2323", "__Sdsd___"],
        required_type="ip_port"
    )

    check_func(
        update_type=update_type,
        values=["1", 3, "333", "2222", 45242422, "22"],
        required_type="int"
    )

    updated_values = converter.UpdateType(config=conf).check()
    debug(updated_values)

    # print("---"*100)
    # from common.converter import UpdateType
    # with open('/ctx/tests/default_configure.yml') as f:
    #     conf = yaml.load(f, Loader=yaml.FullLoader)
    #     UpdateType(config=conf, logger=self.logger).check()
    #     print("**"*100)

