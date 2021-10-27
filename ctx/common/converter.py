#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import string
import random
import binascii
from datetime import datetime


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



