#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import string
import random
import binascii
import re
from datetime import datetime


class UpdateType:
    def __init__(self, config=None, logger=None):
        if config is None:
            config = {}
        self.config = config
        self.logger = logger
        self.required_type = {}
        self.return_result = {}

        self.regex = dict(
            ipaddr=r'((25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[0-9]{1,2})(\.(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[0-9]{1,2})){3})',
            port=r'(:((6553[0-5])|(655[0-2][0-9])|(65[0-4][0-9]{2})|(6[0-4][0-9]{3})|'
                 r'([1-5][0-9]{4})|([0-5]{1,5})|([0-9]{1,4})))?$'
        )

        if self.config.get("settings") and self.config['settings'].get('env'):
            self.settings_env = self.config['settings']['env']

    def check(self):
        self.parse_config()
        for required_key, required_value in self.required_type.items():
            if isinstance(required_value, dict) and required_value.get('default') and required_value.get("type"):
                result = self.check_value_type(required_value.get('default'), required_value.get('type'), key=required_key)
                # debug(result)
                # print(f"required_key={required_key}, value={required_value}, result={result}")
                self.return_result[required_key] = result
        self.update_env_config()
        return self.return_result

    def parse_config(self, config=None):
        if config is None:
            config = self.config
        for config_key, config_value in config.items():
            if self.is_type_dict(config_value):
                self.required_type[config_key] = {
                    "default": config_value['default'],
                    "type": config_value['type'],
                }
            elif isinstance(config_value, dict):
                self.parse_config(config_value)

    def update_env_config(self):
        if self.settings_env:
            for env_key, env_value in self.settings_env.items():
                if env_key:
                    required_type = self.required_type.get(env_key)
                    if required_type:
                        env_value = self.check_value_type(env_value, required_type.get('type'), key=env_key)
                        self.logging(f"[Update] {env_key} = '{env_value}' ({required_type.get('type')})")
                        self.return_result[env_key] = env_value
                    else:
                        self.logging(f"Undefined key: '{env_key}', value:'{env_value}'", "error")

    @staticmethod
    def is_type_dict(value):
        if isinstance(value, dict) and value.get('default', "NOT_NONE") is not "NOT_NONE" and value.get('type'):
            return True
        return False

    @staticmethod
    def fill_not_none_value(value):
        if value is None:
            return ''
        else:
            return value

    def check_value_type(self, value, required_type=None, key=None):
        if required_type is None:
            self.logging(f"{key} required_type is None", "error")

        value = self.fill_not_none_value(value)
        if required_type == "str":
            return_value = str(value)
        elif required_type == "int":
            try:
                return_value = int(value)
            except ValueError:
                self.logging(f"Invalid type {value}", "error")
                raise Exception(f"Invalid type {value}")
        elif required_type == "float":
            return_value = float(value)
        elif required_type == "bool":
            return_value = str2bool(value)
        elif required_type == "array":
            return_value = str(value).split(",")
        elif required_type == "list":
            return_value = str(value).split(",")
        elif required_type == "url":
            if not re.findall(r'((http|https):((//)|(\\\\))+([\w\d:#@%/;$()~_?\+-=\\\.&](#!)?)*)', value):
                self.logging(f"Invalid {key}, required_type={required_type}, value={value}", "error")
            return_value = str(value)
        elif required_type == "ip_port":
            if not re.findall(
                    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
                    r'localhost|'  # localhost...
                    r'(([\w\d:#@%/;$()~_?\+-=\\\.&](#!)?)*)|'
                    rf'^(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[0-9]{1, 2})'
                    r'(\.(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[0-9]{1,2})){3})'
                    r'(:((6553[0-5])|(655[0-2][0-9])|(65[0-4][0-9]{2})|(6[0-4][0-9]{3})|'
                    r'([1-5][0-9]{4})|([0-5]{1,5})|([0-9]{1,4})))$', value):
                self.logging(f"Invalid {required_type}, value={value}", "error")
                raise ValueError(f"Invalid {key}, required_type={required_type}, value={value}")
            return_value = str(value)

        elif required_type == "port":
            if len(re.findall(fr'({self.regex["ipaddr"]})?({self.regex["port"]})', value)) <= 1:
                self.logging(f"Invalid {required_type}, value={value}", "error")
                raise ValueError(f"Invalid {key}, required_type={required_type}, value={value}")
            return_value = str(value)

        else:
            return_value = value
        return return_value

    def logging(self, message=None, level="info"):
        message_text = f"[CheckType] {message}"
        if self.logger:
            if level == "info" and hasattr(self.logger, "info"):
                self.logger.info(message_text)
            elif level == "error" and hasattr(self.logger, "error"):
                self.logger.error(message_text)
            elif level == "warn" and hasattr(self.logger, "warn"):
                self.logger.warn(message_text)
        else:
            print(f"[{level.upper()}]{message_text}")


def random_passwd(digit=8):
    source = string.ascii_letters + string.digits
    return ''.join((random.choice(source) for i in range(digit)))


def convert_bytes(num):
    for x in ['bytes', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0:
            return "%3.1f %s" % (num, x)
        num /= 1024.0


def get_size(file_path, attr=False):
    return_size, file_attr = ["", ""]

    if os.path.isdir(file_path):
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(file_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                # skip if it is symbolic link
                if not os.path.islink(fp):
                    total_size += os.path.getsize(fp)
        return_size = convert_bytes(total_size)
        file_attr = "DIR"
    elif os.path.isfile(file_path):
        file_info = os.stat(file_path)
        return_size = convert_bytes(file_info.st_size)
        file_attr = "FILE"

    if attr:
        return [return_size, file_attr]

    return return_size


def is_hex(s):
    try:
        int(s, 16)
        return True
    except:
        return False


def str2bool(v):
    if v is None:
        return False
    elif type(v) == bool:
        return v
    if v.lower() in ('yes', 'true',  't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        return False


def todaydate(date_type=None):
    if date_type is None:
        return '%s' % datetime.now().strftime("%Y%m%d")
    elif date_type == "file":
        return '%s' % datetime.now().strftime("%Y%m%d_%H%M")
    elif date_type == "time":
        return '%s' % datetime.now().strftime("%H:%M:%S.%f")[:-3]
    elif date_type == "hour":
        return '%s' % datetime.now().strftime("%H%M")
    elif date_type == "ms":
        return '%s' % datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    elif date_type == "log_ms":
        return '%s' % datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    elif date_type == "ms_text":
        return '%s' % datetime.now().strftime("%Y%m%d-%H%M%S%f")[:-3]


def long_to_bytes(val, endianness='big'):
    """
    Use :ref:`string formatting` and :func:`~binascii.unhexlify` to
    convert ``val``, a :func:`long`, to a byte :func:`str`.
    :param long val: The value to pack
    :param str endianness: The endianness of the result. ``'big'`` for
      big-endian, ``'little'`` for little-endian.
    If you want byte- and word-ordering to differ, you're on your own.
    Using :ref:`string formatting` lets us use Python's C innards.
    """
    # one (1) hex digit per four (4) bits
    width = val.bit_length()

    # unhexlify wants an even multiple of eight (8) bits, but we don't
    # want more digits than we need (hence the ternary-ish 'or')
    width += 8 - ((width % 8) or 8)

    # format width specifier: four (4) bits per hex digit
    fmt = '%%0%dx' % (width // 4)

    # prepend zero (0) to the width, to zero-pad the output
    s = binascii.unhexlify(fmt % val)

    if endianness == 'little':
        # see http://stackoverflow.com/a/931095/309233
        s = s[::-1]

    return s


def format_seconds_to_hhmmss(seconds):
    try:
        seconds = int(seconds)
        hours = seconds // (60*60)
        seconds %= (60*60)
        minutes = seconds // 60
        seconds %= 60
        return "%02i:%02i:%02i" % (hours, minutes, seconds)
    except Exception as e:
        return seconds


region_info = {
    "Seoul": "-kr.s3",
    "Tokyo": "-jp.s3",
    "Virginia": "-va.s3",
    "Hongkong": "-hk.s3.ap-east-1",
    "Singapore": "-sg.s3",
    "Mumbai": "-mb.s3",
    "Frankfurt": "-ff.s3",
    "Sydney": "-sy.s3"
}

region_cf_info = {
    "Seoul": "kr/bk",
#    "Tokyo": "jp/bk",
#    "Virginia": "va/bk",
#    "Hongkong": "hk/bk",
#    "Singapore": "sg/bk",
#    "Mumbai": "mb/bk",
#    "Frankfurt": "ff/bk",
#    "Sydney": "sy/bk"
}



