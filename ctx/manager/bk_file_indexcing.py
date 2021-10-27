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


def get_public_ip():
    return requests.get("http://checkip.amazonaws.com").text.strip()


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
                 checksum_filename="checksum.json", worker=20, debug=False, check_method="hash", output_dir="./"):

        self.prefix = prefix
        self.base_dir = base_dir
        self.index_filename = os.path.join(output_dir,index_filename)
        self.checksum_filename = os.path.join(output_dir,checksum_filename)
        self.worker = worker
        self.file_list = []
        self.sliced_file_list = None
        #self.exclude_files = ["ee.sock", "genesis.zip", "icon_genesis.zip"]
        self.exclude_files = ["ee.sock", "icon_genesis.zip", "auth.json", "rconfig.json", "restore", "temp"]
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
        #print (self.file_list, "\n\n\n")

        
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
        #if self.debug:
        #    print(f"[INDEX][{self.count}/{self.total_file_size}] {end:.2f}ms file={dest_file}, size={file_size}, checksum={checksum}")
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
        #print(f' + File save : {self.index_filename}')
        return self.index_filename

    def check(self):
        self.indexed_file_dict = self.open_json(self.checksum_filename)

        for file_name, value in self.indexed_file_dict.items():
            is_ok = True
            fullpath_file = f"{self.base_dir}/{file_name}"
            if not os.path.exists(fullpath_file):
                if self.debug:
                    print(f"[CHECK][NOT FOUND FILE] {fullpath_file}")
                is_ok = False
            else:
                this_file_size = self.get_file_size(fullpath_file)
                if this_file_size != value.get("file_size"):
                    if self.debug:
                        print(f"[CHECK][NOT MATCHED SIZE] {fullpath_file}, {this_file_size}!={value.get('file_size')}", value)
                    is_ok = False

            if is_ok:
                print(f"[CHECK][OK] {fullpath_file}", value)

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
                pass
                #print("[OK] Write json file -> %s, %s" % (filename, self.get_file_size(filename)))
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


def get_parser():
    parser = argparse.ArgumentParser(
        description='recursive file indexing',
        fromfile_prefix_chars='@'
    )
    parser.add_argument('command', choices=["index", "check"])
    parser.add_argument('-d', '--dir', help='destination directory name (default: ./)',
                        default="./")

    parser.add_argument('-o', '--output', help='output directory name (default: ./)',
                        default="./")

    parser.add_argument('-p', '--prefix', help=f'prefix name (default: http://{get_local_ip()}',
                        default=f"http://{get_local_ip()}")

    parser.add_argument('-m', '--check-method', help=f'how to check the method,',
                        choices=["hash", "size"],
                        default=f"size")
    return parser.parse_args()


def main():
    args = get_parser()

    if args.command == "index":
        save_file = FileIndexer(base_dir=args.dir, debug=True, check_method=args.check_method, prefix=args.prefix, output_dir=args.output).run()
    elif args.command == "check":
        save_file = FileIndexer(base_dir=args.dir, debug=True, check_method=args.check_method, prefix=args.prefix, output_dir=args.output).check()

    #print (save_file)
   #### Run ex ) ./bk_file_indexcing.py -d /app/goloop/data/ -p http://download.soliwallet.io/kr/bk/MainNet/20211012/1700 -o /app/goloop/data/temp index


if __name__ == "__main__":
    main()
