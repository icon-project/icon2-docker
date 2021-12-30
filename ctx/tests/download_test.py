#!/usr/bin/env python3
#https://hooks.slack.com/services/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
# from config.configure import Configure
# from common import base, output
# conf = Configure()
# print(conf)



import requests
import yaml

###
import time
import subprocess
from termcolor import cprint
###

import os
import xxhash
import requests
import json
import time
import aiofiles
import asyncio
import datetime
import re
from itertools import zip_longest


def load_yaml(yaml_file):
    """
    Loads a yaml file either on disk at path *yaml_file*,
    or from the URL *yaml_file*.
    Returns a dictionary.
    """
    # try:
    #     r = requests.get(yaml_file, stream=True)
    # except (requests.exceptions.MissingSchema, requests.exceptions.URLRequired):
    #     config = load_local_yaml(yaml_file)

    if yaml_file and yaml_file[:4] == "http":
        r = requests.get(yaml_file, stream=True)
        if r.status_code == 404:
            raise requests.RequestException("404 Not Found!")
        r.raw.decode_content = True
        config = yaml.safe_load(r.raw)
    else:
        config = load_local_yaml(yaml_file)
    return config


def load_local_yaml(file_path):
    """Load yaml file located at file path.

    Parameters
    ----------
    file_path : str
        path to yaml file

    Returns
    -------
    dict
        contents of yaml file

    Raises
    ------
    Exception
        if theres an issue loading file. """
    with open(file_path) as fin:
        content = yaml.safe_load(fin)
    return content


def download_file(url):
    local_filename = url.split('/')[-1]
    # NOTE the stream=True parameter below
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                # If you have chunk encoded response uncomment if
                # and set chunk_size parameter to None.
                #if chunk:
                f.write(chunk)
    return local_filename


class FileIndexer:

    def __init__(self, prefix=None, base_dir="./", index_filename="file_list.txt",
                 checksum_filename="checksum.json", worker=20, debug=False, check_method="hash"):
        self.prefix = prefix
        self.base_dir = base_dir
        self.index_filename = index_filename
        self.checksum_filename = checksum_filename
        self.worker = worker
        self.file_list = []
        self.sliced_file_list = None
        self.exclude_files = ["ee.sock", "genesis.zip", "icon_genesis.zip"]
        self.exclude_extensions = ["sock"]
        self.debug = debug
        self.count = 0
        self.total_file_size = 0

        self.check_method = check_method
        self.indexed_file_dict = {}

    def list_files_recursive(self):
        """
        Function that receives as a parameter a directory path
        :return list_: File List and Its Absolute Paths
        """
        files = []
        for r, d, f in os.walk(self.base_dir):
            for file in f:
                files.append(os.path.join(r, file))

        self.file_list = [file for file in files]
        self.total_file_size = len(self.file_list)
        iterables = [iter(self.file_list)] * self.worker
        self.sliced_file_list = zip_longest(*iterables, fillvalue=None)

    def is_exclude_list(self, dest_string):
        for exclude in self.exclude_files:
            if exclude in dest_string:
                return False
        root, extension = os.path.splitext(dest_string)
        if extension:
            extension = extension.replace(".", "")
            if extension in self.exclude_extensions:
                return False
        return True

    async def async_executor(self, file_list):
        tasks = []
        for file in file_list:
            if file and self.is_exclude_list(file):
                tasks.append(asyncio.ensure_future(self.parse_async(file)))
        await asyncio.gather(*tasks)

    async def get_xxhash_async(self, file_path):
        async with aiofiles.open(file_path, "rb") as fd:
            content = await fd.read()
            # md5_hash = xxhash.xxh64(content).hexdigest()
            # md5_hash = xxhash.xxh32(content, seed=0).hexdigest()
            return xxhash.xxh3_64_hexdigest(content)

    async def parse_async(self, file_path: str):
        start = time.time()
        checksum = None
        if self.check_method == "hash":
            checksum = await self.get_xxhash_async(file_path)
            # checksum = await self.adler32sum(file_path)

        file_size = self.get_file_size(file_path)
        dest_file = re.sub(rf"^{self.base_dir}", "", file_path)
        dest_file = re.sub(rf"^\/", "", dest_file)
        download_url = f"{self.prefix}/{dest_file}"

        self.indexed_file_dict[dest_file] = {
            "file_size": file_size,
            "checksum": checksum
        }

        async with aiofiles.open(self.index_filename, mode='+a') as f:
            await f.write(f"{download_url}\n"
                          f"\tout={dest_file}\n")

        end = time.time() - start
        if self.debug:
            print(f"[INDEX][{self.count}/{self.total_file_size}] {end:.2f}ms file={dest_file}, size={file_size}, checksum={checksum}")
        self.count += 1
        return checksum

    def run(self):
        if os.path.exists(self.index_filename):
            os.remove(self.index_filename)
        if os.path.exists(self.checksum_filename):
            os.remove(self.checksum_filename)

        self.list_files_recursive()
        for file_list in self.sliced_file_list:
            asyncio.run(self.async_executor(file_list))
        self.write_json(self.checksum_filename, self.indexed_file_dict)

    def check(self):
        self.indexed_file_dict = self.open_json(self.checksum_filename)

        result = {
            "not_found": [],
            "not_size": []
        }
        for file_name, value in self.indexed_file_dict.items():
            is_ok = True
            fullpath_file = f"{self.base_dir}/{file_name}"
            if not os.path.exists(fullpath_file):
                if self.debug:
                    print(f"[CHECK][NOT FOUND FILE] {fullpath_file}")
                    result["not_found"].append(fullpath_file)
                is_ok = False
            else:
                this_file_size = self.get_file_size(fullpath_file)
                if this_file_size != value.get("file_size"):
                    if self.debug:
                        print(f"[CHECK][NOT MATCHED SIZE] {fullpath_file}, {this_file_size}!={value.get('file_size')}", value)
                        result["not_size"].append(fullpath_file)
                    is_ok = False

            if is_ok:
                print(f"[CHECK][OK] {fullpath_file}", value)

        return result

    @staticmethod
    def get_file_size(file_path):
        """
        this function will return the file size
        """
        if os.path.isfile(file_path):
            file_info = os.stat(file_path)
            return file_info.st_size

    @staticmethod
    def json_default(value):
        if isinstance(value, datetime.date):
            return value.strftime('%Y-%m-%d %H:%M:%S')
        raise TypeError("not JSON serializable")

    def write_json(self, filename, data):
        try:
            with open(filename, "w") as outfile:
                json.dump(data, outfile, default=self.json_default)
            if os.path.exists(filename):
                print("[OK] Write json file -> %s, %s" % (filename, self.get_file_size(filename)))
        except:
            # cprint(f"path not found {filename}", "red")
            print(f"[ERROR] can't write to json -> {filename}")
            raise

    @staticmethod
    def open_json(filename):
        try:
            with open(filename, "r") as json_file:
                return json.loads(json_file.read())
        except Exception as e:
            print(f"[ERROR] can't open to json -> {filename} - {e}")
            raise


def run_execute(text=None, cmd=None, cwd=None, check_output=True, capture_output=True, hook_function=None, debug=False):
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

    if check_output:
        cprint(f"[START] run_execute(), {text}", "green")

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
                        hook_function(line=line_striped, line_no=result['line_no'])

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
            cprint(f"[FAIL] {text}, Error = '{result.get('stderr')}'", "red")
        else:
            cprint(f"[ OK ] {text}, timed={end}", "green")
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

    if kwargs.get("line_no") % 1000 == 0:
        print(f"[output hook - matching line_no] {args} {kwargs}")


def todaydate(type=None):
    from datetime import datetime
    if type is None:
        return '%s' % datetime.now().strftime("%Y%m%d")
    elif type == "ms":
        return '[%s]' % datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    elif type == "ms_text":
        return '%s' % datetime.now().strftime("%Y%m%d-%H%M%S%f")[:-3]


def write_logging(**kwargs):
    log_path = "./"
    log_name = "download"
    log_file_name = f"{log_path}/%s_%s.log" % (log_name, todaydate())

    if os.path.isdir(log_path) is False:
        os.mkdir(log_path)

    logfile = open(log_file_name, "a+")
    logfile.write(f"{todaydate('ms')}, {kwargs.get('line')}  \n")
    logfile.close()


# run_execute(cmd="ls -al", capture_output=False, hook_function=write_logging)
# exit()

# stage2_file_list = "http://172.31.5.112/stage2.yml"
# stage2_info = load_yaml(stage2_file_list)
# index_filename = download_file(stage2_info.get('INDEX_URL'))
# checksum_filename = download_file(stage2_info.get('CHECKSUM_URL'))

# index_filename = download_file("https://dn.solidwallet.io/MainNet/20211019/file_list.txt")
# checksum_filename = download_file("https://dn.solidwallet.io/MainNet/20211019/checksum.json")

# print(index_filename, checksum_filename)

download_base_dir = "data"

# stage_2_file_list = "https://networkinfo.solidwallet.io/info/mainnet.json"
# stage2_info = requests.get(stage_2_file_list).json()

# index_filename = download_file(stage2_info.get('index_url'))
# checksum_filename = download_file(stage2_info.get('checksum_url'))

index_filename = download_file("https://icon2-backup-kr.s3.ap-northeast-2.amazonaws.com/s3sync/SejongNet/file_list.txt")


# print(stage2_info)
# exit()
aric2c_cmd = f"aria2c -d {download_base_dir} -i {index_filename} " \
             f" -V -j20 -x16 --http-accept-gzip --check-certificate=false" \
             f" --conditional-get --disk-cache=64M  --allow-overwrite --log-level=error --log download_error.log -c"


print(aric2c_cmd)

run_execute(cmd=aric2c_cmd, capture_output=False, hook_function=print)

check_result = FileIndexer(base_dir=download_base_dir, debug=True, check_method="check").check()

print(check_result)
# res = base.run_execute("ls -al")
# output.dump(res)
#
#
#
