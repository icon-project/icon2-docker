#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import yaml
import requests
import socket
import datetime
import inspect

from glob import glob
from termcolor import cprint
from common import converter, base
from config.configure import Configure as CFG
import getpass
import yaml

cfg = CFG()


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    WHITE = '\033[97m'


def get_bcolors(text, color, bold=False, underline=False, width=None):
    if width and len(text) <= width:
        text = text.center(width, ' ')
    return_text = f"{getattr(bcolors, color)}{text}{bcolors.ENDC}"
    if bold:
        return_text = f"{bcolors.BOLD}{return_text}"
    if underline:
        return_text = f"{bcolors.UNDERLINE}{return_text}"
    return str(return_text)


def colored_input(message, password=False, color="WHITE"):
    input_message = get_bcolors(text=message, color=color, bold=True, underline=True) + " "
    if password:
        return getpass.getpass(input_message)
    return input(input_message)


def check_file_overwrite(filename):
    exist_file = False
    if filename and is_file(filename):
        cprint(f"File already exists => {filename}", "green")
        exist_file = True

    if exist_file:
        answer = colored_input(f"Overwrite already existing '{filename}' file? (y/n)")
        if answer == "y":
            cprint(f"Remove the existing keystore file => {filename}", "green")
            os.remove(filename)
        else:
            cprint("Stopped", "red")
            sys.exit(127)


def get_file_path(filename):
    dirname, file = os.path.split(filename)
    extension = os.path.splitext(filename)[1]

    return {
        "dirname": dirname,
        "file": file,
        "extension": extension,
        "filename": filename
    }


def is_file(filename):
    if "*" in filename:
        if len(glob(filename)) > 0:
            return True
        else:
            return False
    else:
        return os.path.exists(os.path.expanduser(filename))


def is_binary_string(filename):
    text_chars = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)) - {0x7f})
    fh = open(filename, 'rb').read(100)
    return bool(fh.translate(None, text_chars))


def is_json(json_file):
    try:
        with open(json_file, 'r', encoding="utf-8-sig") as j:
            json.loads(j.read())
    except ValueError as e:
        return False
    return True


def open_json(filename):
    try:
        with open(filename, "r") as json_file:
            return json.loads(json_file.read())
    except Exception as e:
        cfg.logger.error(f"[ERROR] can't open the json -> {filename} - {e}")
        raise


def open_file(filename):
    try:
        with open(filename, "r") as file:
            return file.read()
    except Exception as e:
        cfg.logger.error(f"[ERROR] can't open the file -> {filename} - {e}")
        raise


def open_yaml_file(filename):
    read_yaml = open_file(filename)
    return yaml.load(read_yaml, Loader=yaml.FullLoader)


def write_file(filename, data, option='w', permit='664'):
    with open(filename, option) as outfile:
        outfile.write(data)
    os.chmod(filename, int(permit, base=8))
    if os.path.exists(filename):
        return "Write file -> %s, %s" % (filename, converter.get_size(filename))  # if __main__.args.verbose > 0 else False
    else:
        return "write_file() can not write to file"


def write_json(filename, data, option='w', permit='664'):
    with open(filename, option) as outfile:
        json.dump(data, outfile)
    os.chmod(filename, int(permit, base=8))
    if os.path.exists(filename):
        return "Write json file -> %s, %s" % (filename, converter.get_size(filename))  # if __main__.args.verbose > 0 else False
    else:
        return "write_json() can not write to json"


def write_yaml(filename, data, option='w', permit='664'):
    with open(filename, option) as outfile:
        yaml.dump(data, outfile)
    os.chmod(filename, int(permit, base=8))
    if os.path.exists(filename):
        return "Write json file -> %s, %s" % (filename, converter.get_size(filename))  # if __main__.args.verbose > 0 else False
    else:
        return "write_json() can not write to json"


def dump(obj, nested_level=0, output=sys.stdout, hex_to_int=False):
    spacing = '   '
    def_spacing = '   '
    if type(obj) == dict:
        print('%s{' % (def_spacing + (nested_level) * spacing))
        for k, v in obj.items():
            if hasattr(v, '__iter__'):
                print(bcolors.OKGREEN + '%s%s:' % (def_spacing + (nested_level + 1) * spacing, k) + bcolors.ENDC, end="")
                dump(v, nested_level + 1, output, hex_to_int)
            else:
                # print >>  bcolors.OKGREEN + '%s%s: %s' % ( (nested_level + 1) * spacing, k, v) + bcolors.ENDC
                print(bcolors.OKGREEN + '%s%s:' % (def_spacing + (nested_level + 1) * spacing, k) + bcolors.WARNING + ' %s' % v + bcolors.ENDC,
                      file=output)
        print('%s}' % (def_spacing + nested_level * spacing), file=output)
    elif type(obj) == list:
        print('%s[' % (def_spacing + (nested_level) * spacing), file=output)
        for v in obj:
            if hasattr(v, '__iter__'):
                dump(v, nested_level + 1, output, hex_to_int)
            else:
                print(bcolors.WARNING + '%s%s' % (def_spacing + (nested_level + 1) * spacing, v) + bcolors.ENDC, file=output)
        print('%s]' % (def_spacing + (nested_level) * spacing), file=output)
    else:
        if hex_to_int and converter.is_hex(obj):
            print(bcolors.WARNING + '%s%s' % (def_spacing + nested_level * spacing, str(round(int(obj, 16) / 10 ** 18, 8)) + bcolors.ENDC))
        else:
            print(bcolors.WARNING + '%s%s' % (def_spacing + nested_level * spacing, obj) + bcolors.ENDC)


def classdump(obj):
    for attr in dir(obj):
        if hasattr(obj, attr):
            value = getattr(obj, attr)
            print(bcolors.OKGREEN + f"obj.{attr} = " + bcolors.WARNING + f"{value}" + bcolors.ENDC)


def kvPrint(key, value, color="yellow"):
    key_width = 9
    key_value = 3
    print(bcolors.OKGREEN + "{:>{key_width}} : ".format(key, key_width=key_width) + bcolors.ENDC, end="")
    print(bcolors.WARNING + "{:>{key_value}} ".format(str(value), key_value=key_value) + bcolors.ENDC)


def print_json(obj, **kwargs):
    if isinstance(obj, dict) or isinstance(obj, list):
        print(json.dumps(obj, **kwargs))
    else:
        print(obj)


def get_level_color(c_level):
    default_color = "5be312"
    return dict(
        info="5be312",
        warn="f2c744",
        warning="f2c744",
        error="f70202",
    ).get(c_level, default_color)


def slack_wh_send(self, text):
    payload = {"text": text}
    if self.config.get('SLACK_WH_URL'):
        requests.post(self.config['SLACK_WH_URL'], json=payload, verify=False)


# def exception_handler(exception_type, exception, traceback):
#     # import inspect
#     # import traceback as traceback_module
#     # from devtools import debug
#     # debug(traceback_module.extract_stack()[:-3])
#     exception_string = f"[Exception] {exception_type.__name__}: {exception}, {traceback.tb_frame}"
#     cprint(f"{exception_string}", "red")
#     cfg.logger.error(f"{exception_string}")


def send_slack(url, msg_text, title=None, send_user_name="CtxBot", msg_level='info'):
    if title:
        msg_title = title
    else:
        msg_title = msg_text
    msg_level = msg_level.lower()

    if url is None:
        cprint("[ERROR] slack webhook url is None", "red")
        return False
    p_color = get_level_color(msg_level)

    payload = {
        # https://app.slack.com/block-kit-builder
        "username": send_user_name,
        "text": msg_title,
        "blocks": [
            {"type": "divider"}
        ],
        "attachments": [
            {
                "color": "#" + p_color,
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "plain_text",
                            "text": f'Job Title : {msg_title}'
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "plain_text",
                            "text": f'{"+ [HOST]":^12s} : {socket.gethostname()}, {base.get_public_ipaddr()}'
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "plain_text",
                            "text": f'{"+ [DATE]":^12s} : {(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3])}'
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "plain_text",
                            "text": f'{"+ [DESC]":^12s} : {msg_text}'
                        }
                    }
                ]
            }
        ]
    }
    try:
        post_result = requests.post(url, json=payload, verify=False, timeout=15)
        if post_result and post_result.status_code == 200 and post_result.text == "ok":
            cfg.logger.info(f"[OK][Slack] Send slack")
            return True
        else:
            cfg.logger.error(f"[ERROR][Slack] Got errors, status_code={post_result.status_code}, text={post_result.text}")
            return False

    except Exception as e:
        cfg.logger.error(f"[ERROR][Slack] Got errors -> {e}")
        return False
