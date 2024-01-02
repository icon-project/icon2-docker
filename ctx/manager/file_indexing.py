#!/usr/bin/env python3
import os
import xxhash
import requests
import socket
import argparse
import json
import time
import aiofiles
import asyncio
import datetime
import re
from itertools import zip_longest
from termcolor import cprint
from pawnlib.output import open_file, open_json
from pawnlib.config import pawn



# def get_public_ip():
#     return requests.get("http://checkip.amazonaws.com").text.strip()


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        ipaddr = s.getsockname()[0]
    except Exception:
        ipaddr = '127.0.0.1'
    finally:
        s.close()
    return ipaddr


class FileIndexer:

    def __init__(self, prefix=None, base_dir="./", index_filename="file_list.txt",
                 checksum_filename="checksum.json", worker=20, debug=False, check_method="hash", output_path="",
                 exclude_files=None,
                 ):
        self.prefix = prefix
        self.base_dir = base_dir
        self.index_filename = index_filename
        self.checksum_filename = checksum_filename
        self.worker = worker
        self.file_list = []
        self.file_list_all = []
        self.sliced_file_list = None
        if exclude_files is None:
            exclude_files = ["ee.sock", "icon_genesis.zip", "download.py"]
        self.exclude_files = exclude_files
        self.exclude_extensions = ["sock"]
        self.debug = debug
        self.count = 1
        self.total_file_count = 0
        self.url_dict = {}

        if output_path:
            if not os.path.isdir(output_path):
                raise ValueError(f"output_path not found - {output_path}")

            self.index_filename = os.path.join(output_path, self.index_filename)
            self.checksum_filename = os.path.join(output_path, self.checksum_filename)

        self.result = {
            "status": "OK",
            "error": {}
        }

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

        self.file_list_all = [file for file in files]
        self.file_list = []
        for file in self.file_list_all:
            if file and self.is_exclude_list(file):
                self.file_list.append(file)

        self.total_file_count = len(self.file_list)

        iterables = [iter(self.file_list)] * self.worker
        self.sliced_file_list = zip_longest(*iterables, fillvalue=None)

    def is_exclude_list(self, dest_string):
        for exclude in self.exclude_files:
            if exclude in dest_string:
                return False
        _ , extension = os.path.splitext(dest_string)
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

    async def get_xxhash_async(self, file_path, last_end_bytes=10240):
        async with aiofiles.open(file_path, "rb") as fd:
            await fd.seek(0, 2)
            end_bytes = await fd.tell()
            if end_bytes and isinstance(end_bytes, int) and end_bytes >= last_end_bytes:
                await fd.seek(end_bytes-last_end_bytes, 0)
            else:
                await fd.seek(0)
            content = await fd.read()
            return xxhash.xxh3_64_hexdigest(content)

    def get_xxhash(self, file_path, last_end_bytes=10240):
        with open(file_path, "rb") as fd:
            fd.seek(0, 2)
            end_bytes = fd.tell()
            if end_bytes and isinstance(end_bytes, int) and end_bytes >= last_end_bytes:
                fd.seek(end_bytes-last_end_bytes, 0)
            else:
                fd.seek(0)
            content = fd.read()
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
            pawn.console.log(f"[INDEX][{self.count:>4}/{self.total_file_count:<4}] {end:.2f}ms file={dest_file:<40}, size={file_size:<10}, checksum={checksum}")
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

    def set_result(self, file_path, key, value):
        full_file_path = f"{self.base_dir}/{file_path}"
        # full_file_path = file_path

        if self.result['error'].get(full_file_path) is None:
            self.result['error'][full_file_path] = {}

        self.result['error'][full_file_path][key] = value

        if self.url_dict.get(file_path):
            self.result['error'][full_file_path].update(self.url_dict.get(file_path))

        self.result['status'] = "FAIL"

    def create_url_dict(self, file_content=""):
        """
        Create a dictionary from a string containing URLs and output paths.
        Each 'out' path is a key, and the corresponding URL is the value.

        :param file_content: String containing the URLs and output paths.
        :return: Dictionary with output paths as keys and URLs as values.
        """
        if not file_content:
            file_content = open_file(self.index_filename)

        url_dict = {}
        if file_content:
            lines = file_content.strip().split('\n')
            last_url = None
            for line in lines:
                line = line.strip()
                if line.startswith('http://') or line.startswith('https://'):
                    last_url = line
                elif line.startswith('out=') and last_url is not None:
                    out = line.split('=')[1].strip()
                    url_dict[out] = {
                        "url": last_url,
                        "out": line
                    }
                    # url_dict[out] = line
                    last_url = None
                else:
                    continue
        return url_dict

    def check_file(self, file_name, value):
        full_path_file = f"{self.base_dir}/{file_name}"
        is_ok_file_exists = os.path.exists(full_path_file)
        is_ok_file_size = is_ok_file_checksum = True
        this_checksum = this_file_size = None

        if not is_ok_file_exists:
            if self.debug:
                pawn.console.log(f"[CHECK][NOT FOUND FILE] {full_path_file}")
            self.set_result(file_name, "file_exists", False)
            return False, this_file_size, this_checksum

        this_file_size = self.get_file_size(full_path_file)
        if this_file_size != value.get("file_size"):
            if self.debug:
                pawn.console.log(f"[CHECK][NOT MATCHED SIZE] {full_path_file}, {this_file_size} != {value.get('file_size')}")
            is_ok_file_size = False

        if self.check_method == "hash":
            this_checksum = self.get_xxhash(full_path_file)
            if this_checksum != value.get("checksum"):
                if self.debug:
                    pawn.console.log(f"[CHECK][NOT MATCHED HASH] {full_path_file}, {this_checksum} != {value.get('checksum')}")
                is_ok_file_checksum = False

        return is_ok_file_exists and is_ok_file_size and is_ok_file_checksum, this_file_size, this_checksum

    def check(self):
        self.url_dict = self.create_url_dict()
        self.indexed_file_dict = self.open_json(self.checksum_filename) if not isinstance(self.checksum_filename, dict) else self.checksum_filename

        for file_name, value in self.indexed_file_dict.items():
            is_ok, this_file_size, this_checksum = self.check_file(file_name, value)
            message = f"{self.base_dir}/{file_name:<40}, is_file={is_ok}, size={is_ok}({this_file_size} / {value.get('file_size')}) checksum={is_ok}({this_checksum} / {value.get('checksum')})"

            if self.debug:
                pawn.console.log(message)

        if self.result.get('error') and self.result['error']:
            self.result['status'] = "FAIL"
            self.result['date'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        return self.result

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


def get_parser():
    parser = argparse.ArgumentParser(
        description='recursive file indexing',
        fromfile_prefix_chars='@'
    )
    parser.add_argument('command', choices=["index", "check"])
    parser.add_argument('-d', '--dir', help='destination directory name (default: ./)',
                        default="./")

    parser.add_argument('-p', '--prefix', help=f'prefix name (default: http://{get_local_ip()}',
                        default=f"http://{get_local_ip()}")

    parser.add_argument('-m', '--check-method', help=f'how to check the method,',
                        choices=["hash", "size"],
                        default=f"hash")

    parser.add_argument('-v', '--verbose', action='count', help=f'verbose mode. view level', default=0)

    return parser.parse_args()


def main():
    args = get_parser()

    if args.verbose > 0:
        debug = True
    else:
        debug = False

    if args.command == "index":
        FileIndexer(base_dir=args.dir, debug=debug, check_method=args.check_method, prefix=args.prefix).run()
    elif args.command == "check":
        res = FileIndexer(base_dir=args.dir, debug=debug, check_method=args.check_method, prefix=args.prefix).check()

        for file, result in res.items():
            print(file, result)


if __name__ == "__main__":
    main()
