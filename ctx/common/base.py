#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import json
import string
import random
import requests
import time
import subprocess

from glob import glob
from termcolor import cprint
from common import converter
from config.configure import Configure as CFG
from ffcount import ffcount

cfg = CFG()


class cd:
    """Context manager for changing the current working directory"""
    def __init__(self, new_path):
        self.new_path = os.path.expanduser(new_path)

    def __enter__(self):
        self.saved_path = os.getcwd()
        os.chdir(self.new_path)

    def __exit__(self, etype, value, traceback):
        os.chdir(self.saved_path)


def run_execute(text=None, cmd=None, cwd=None, check_output=True, capture_output=True, hook_function=None, debug=False, **kwargs):
    """
    Helps run commands
    :param text: just a title name
    :param cmd: command to be executed
    :param cwd: the function changes the working directory to cwd
    :param check_output:
    :param capture_output:
    :param hook_function:
    :param debug:
    :return:
    """
    if cmd is None:
        cmd = text

    start = time.time()

    result = dict(
        stdout=[],
        stderr=None,
        return_code=0,
        line_no=0
    )

    if text != cmd:
        text = f"text='{text}', cmd='{cmd}' :: "
    else:
        text = f"cmd='{cmd}'"

    # if check_output:
    #     # cprint(f"[START] run_execute(), {text}", "green")
    #     cfg.logger.info(f"[START] run_execute() , {text}")
    try:
        # process = subprocess.run(cmd, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd)
        process = subprocess.Popen(cmd, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd, shell=True)

        for line in process.stdout:
            line_striped = line.strip()
            if line_striped:
                if callable(hook_function):
                    if hook_function == print:
                        print(f"[{result['line_no']}] {line_striped}")
                    else:
                        hook_function(line=line_striped, line_no=result['line_no'], **kwargs)

                if capture_output:
                    result["stdout"].append(line_striped)
                result['line_no'] += 1

        out, err = process.communicate()

        if process.returncode:
            result["return_code"] = process.returncode
            result["stderr"] = err.strip()

    except Exception as e:
        result['stderr'] = e
        raise OSError(f"Error while running command cmd='{cmd}', error='{e}'")

    end = round(time.time() - start, 3)

    if check_output:
        if result.get("stderr"):
            # cprint(f"[FAIL] {text}, Error = '{result.get('stderr')}'", "red")
            cfg.logger.error(f"[FAIL] {text}, Error = '{result.get('stderr')}'")
        else:
            # cprint(f"[ OK ] {text}, timed={end}", "green")
            cfg.logger.info(f"[ OK ] {text}, timed={end}")
    return result


def hook_print(*args, **kwargs):
    """
    Print to output every 10th line
    :param args:
    :param kwargs:
    :return:
    """
    if "amplify" in kwargs.get("line"):
        print(f"[output hook - matching keyword] {args} {kwargs}")

    if kwargs.get("line_no") % 100 == 0:
        print(f"[output hook - matching line_no] {args} {kwargs}")
    # print(kwargs.get('line'))


def write_logging(**kwargs):
    log_file_name = None

    if kwargs.get('log_filename'):
        log_file_name = kwargs['log_filename']

    log_message = f"[{kwargs.get('line_no')}]{converter.todaydate('ms')}, {kwargs.get('line')}"

    if kwargs.get("line_no") % 100 == 0:
        file_count_string = ""
        if kwargs.get('total_file_count'):
            number_of_files, number_of_dirs = ffcount("/goloop/data")
            file_count_string = f"[{number_of_files}/{kwargs['total_file_count']}]"
        cfg.logger.info(f"{file_count_string} {log_message}")

    logfile = open(log_file_name, "a+")
    logfile.write(f"{log_message} \n")
    logfile.close()


def disable_ssl_warnings():
    from urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


def get_public_ipaddr():
    try:
        return requests.get("http://checkip.amazonaws.com", verify=False).text.strip()
    except:
        return None


def is_docker():
    return converter.str2bool(os.environ.get("IS_DOCKER", False))
