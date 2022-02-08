#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import append_parent_path

from config.configure import Configure as CFG
from common import output, converter, base

import threading
import boto3
from botocore.handlers import disable_signing

import os, time, datetime
import sys
import zipfile
import argparse
from termcolor import colored, cprint
from boto3.s3.transfer import TransferConfig
from halo import Halo
import requests
from multiprocessing.pool import ThreadPool
from timeit import default_timer

version = "0.3"
region_info = {
    "Seoul": ".s3",
    "Tokyo": "-jp.s3",
    "Virginia": "-va.s3",
    "Hongkong": "-hk.s3.ap-east-1",
    # "Singapore": "-sg.s3",
    # "Mumbai"   : "-mb.s3",
    # "Frankfurt": "-ff.s3",
}


def find_fastest_region(verbose=0):
    results = {}
    pool = ThreadPool(6)
    region_cnt = 0

    spinner = Halo(text=f"Finding fastest region", spinner='dots')
    spinner.start()

    for region_name, region_code in region_info.items():
        url = f'https://icon-leveldb-backup{region_code}.amazonaws.com/route_check'
        exec_func = "get_connect_time"
        exec_args = (f"{url}", region_name)
        results[region_cnt] = {}
        results[region_cnt]["data"] = pool.apply_async(getattr(sys.modules[__name__], exec_func), exec_args)
        region_cnt += 1
    pool.close()
    pool.join()

    last_latency = {}
    for i, p in results.items():
        data = p['data'].get()
        print(f"data => {data}") if verbose > 0 else False
        if time is not None:
            if len(last_latency) == 0:
                last_latency = data
            if last_latency.get("time") and data.get("time"):
                if last_latency.get("time", 99999) >= data.get("time"):
                    last_latency = data
        print(data) if verbose else False
    spinner.succeed(f'[Done] Finding fastest region')
    return last_latency


def get_connect_time(url, name="NULL"):
    status_code = 999
    try:
        response = requests.get(f'{url}', timeout=5)
        response_text = response.text
        elapsed_time = response.elapsed.total_seconds()
        status_code = response.status_code
    except Exception as e:
        elapsed_time = None
        response_text = None
        cprint(f"get_connect_time error : {url} -> {sys.exc_info()[0]} / {e}", "red")
    return {"url": url, "time": elapsed_time, "name": name, "text": response_text, "status": status_code}


def catchMeIfYouCan(encoded_text, encode_key=None):
    from cryptography.fernet import Fernet
    cipher_suite = Fernet(encode_key)
    decoded_text = cipher_suite.decrypt(encoded_text)
    kkk, sss = decoded_text.decode('utf-8').split(",")
    return kkk, sss


def multi_part_upload_with_s3(filename=None, key_path=None, bucket=None, upload_type="single", enc_keys=None):
    if enc_keys is None:
        enc_keys = {}

    start_time = default_timer()
    bucket_name_prefix = "prep-logs"
    key, sec = catchMeIfYouCan(encoded_text=enc_keys.get('aawwss_text'), encode_key=enc_keys.get('encode_key'))
    aaa_env, sss_env = catchMeIfYouCan(encoded_text=enc_keys.get('aawwss_env'), encode_key=enc_keys.get('encode_key'))
    os.environ[aaa_env] = key
    os.environ[sss_env] = sec
    if bucket is None or bucket == "":
        BUCKET_NAME = f"{bucket_name_prefix}-kr"
    else:
        BUCKET_NAME = f"{bucket_name_prefix}{bucket}"
    cprint(f"\t bucket {bucket} -> {BUCKET_NAME}") if args.verbose else False
    if bucket == "-hk":
        s3 = boto3.resource(
            's3',
            region_name="ap-east-1"
        )
    else:
        s3 = boto3.resource(
            's3',
        )
    if upload_type == "multi":
        config = TransferConfig(multipart_threshold=1024 * 25, max_concurrency=10,
                                multipart_chunksize=1024 * 25, use_threads=True)
    else:
        config = TransferConfig(multipart_threshold=838860800, max_concurrency=10, multipart_chunksize=8388608,
                                num_download_attempts=5, max_io_queue=100, io_chunksize=262144, use_threads=True)
    if filename is None:
        cprint(f"[ERROR] filename is None", "red")
        raise SystemExit()
    if key_path is None:
        key_path = filename
    try:
        s3.meta.client.upload_file(filename, BUCKET_NAME, key_path,
                                   # ExtraArgs={'ACL': 'public-read', 'ContentType': 'text/pdf'},
                                   Config=config,
                                   Callback=ProgressPercentage(filename)
                                   )
    except Exception as e:
        e = str(e).replace(":", ":\n")
        cprint(f"\n[ERROR] File upload fail / cause->{e}\n", "red")
        raise SystemExit()

    elapsed = default_timer() - start_time
    time_completed_at = "{:5.3f}s".format(elapsed)

    cprint(f"\n\t time_completed_at = {time_completed_at}")


class ProgressPercentage(object):
    def __init__(self, filename):
        self._filename = filename
        self._size = float(os.path.getsize(filename))
        self._seen_so_far = 0
        self._lock = threading.Lock()
        self._prevent_bytes = 0

    def __call__(self, bytes_amount):
        with self._lock:
            self._seen_so_far += bytes_amount
            percentage = (self._seen_so_far / self._size) * 100
            sys.stdout.write(
                "\r \t %s  %s / %s  (%.2f%%) " % (
                    self._filename, self._seen_so_far, self._size,
                    percentage))
            sys.stdout.flush


def check_file_type(filename):
    if os.path.isdir(filename):
        return "dir"
    elif os.path.isfile:
        return "file"


def get_file_info(file):
    file_type = None
    if os.path.isdir(file):
        file_type = "dir"
    elif os.path.isfile(file):
        file_type = "file"
    try:
        file_info = os.stat(file)
        return_result = {
            "full_filename": file,
            "size": converter.convert_bytes(file_info.st_size),
            "date": datetime.datetime.fromtimestamp(file_info.st_mtime),
            "unixtime": file_info.st_mtime,
            "type": file_type
        }
    except:
        return_result = {
            "full_filename": file,
            "size": None,
            "date": None,
            "unixtime": None,
            "type": None
        }

    return return_result


def get_parser():
    parser = argparse.ArgumentParser(description='Send me log')
    parser.add_argument('-f', '--find', action='count', help=f'Find fastest region, just checking', default=0)
    parser.add_argument('--network', type=str, help=f'Network name', choices=["MainNet", "SejongNet"], default="MainNet")
    parser.add_argument('-d', '--log-dir', metavar='log-dir', type=str, help=f'log directory location', default=None)
    parser.add_argument('--static-dir', metavar='static-dir', type=str, nargs="+", help=f'include log directory location', default=None)

    parser.add_argument('--include-dir', metavar='include-dir', type=str, nargs="+", help=f'include log directory location', default=None)
    parser.add_argument('--exclude-dir', metavar='exclude-dir', type=str, nargs="+", help=f'exclude log directory location', default=None)

    parser.add_argument('-td', '--target-date', type=str, help=f'upload target date', default=f'today')
    parser.add_argument('-n', '--name', type=str, help=f'Set filename for upload ', default=None)
    parser.add_argument('-u', '--upload', action='count', help=f'force upload mode', default=0)
    parser.add_argument('-uf', '--upload-filename', type=str, help=f'upload upload mode', default=0)
    parser.add_argument('-ut', '--upload-type', type=str, help=f'upload type', choices=["single", "multi"], default="multi")
    parser.add_argument('-v', '--verbose', action='count', help=f'verbose mode ', default=0)
    parser.add_argument('-r', '--region', metavar="region", type=str, help=f'region ', default=None)
    return parser


class SendLog:
    def __init__(
            self,
            verbose,
            region=None,
            network=None,
            enc_keys=None,
            upload_filename=None,
            log_dir=None,
            upload_target_date="today",
            answer="y",
            exclude_dir=None
    ):

        if enc_keys is None:
            enc_keys = {}
        self.verbose = verbose
        self.region = region
        self.network = network
        self.enc_keys = enc_keys
        self.upload_target_date = upload_target_date
        self.answer = answer
        self.exclude_dir = exclude_dir
        self.region_info = {}
        self.upload_filename = upload_filename
        self.log_dir = log_dir
        self.last_modified = ""

        self.file_list = []
        self.upload_target_files = []

    def run(self):
        self._prepare()
        self.find_log()
        self.compress_zip()
        self.upload_files()

    def upload_files(self):
        if self.answer:
            answer = self.answer
        else:
            answer = input("\n Are you going to upload it? It will be send to ICONLOOP's S3 (y/n)")

        if answer == "y":
            if self.region:
                self.region_info = {
                    'url': f'https://icon-leveldb-backup.{region_info.get(self.region)}.amazonaws.com/route_check',
                    'time': 0,
                    'name': self.region,
                    'text': 'OK\n',
                    'status': 200
                }
            else:
                self.region_info = find_fastest_region(verbose=self.verbose)

            bucket_code = (region_info.get(self.region_info.get("name")).split("."))[0]
            cprint(f'[OK] Fastest region -> {self.region_info.get("name")}', "green")
            output.kvPrint(f'bucket_code', bucket_code) if args.verbose else False
            multi_part_upload_with_s3(
                filename=f"{self.upload_filename}",
                key_path=f"{self.network}/{self.upload_filename}",
                bucket=bucket_code,
                upload_type="multi",
                enc_keys=self.enc_keys
            )
            cprint(f"\n[OK] File uploaded successfully", "green")
        else:
            cprint("\n Stopped", "red")

    def find_log(self):
        if check_file_type(self.log_dir) == "dir":
            self.last_modified = get_file_info(self.log_dir).get("date")
            print(self.last_modified)
        else:
            cprint(f"[ERROR] '{self.log_dir}' is not directory", "red")
            raise SystemExit()

        print(f"dirname = {self.log_dir}")

        try:
            filenames = os.listdir(self.log_dir)
        except Exception as e:
            cprint(f"Error: '{self.log_dir}' - {e}", "red")
            raise SystemExit()

        for filename in filenames:
            full_filename = os.path.join(self.log_dir, filename)
            file_info = get_file_info(full_filename)
            self.file_list.append(file_info)

        output.kvPrint("Your log directory", f'{self.log_dir} \t\t[{self.last_modified}]')
        output.kvPrint("Target date", self.upload_target_date)
        output.kvPrint("Excluding directory", self.exclude_dir)
        cprint(f"\n---------- Found log files ({self.upload_target_date})  ----------", "white")

        today = datetime.datetime.today().strftime("%Y-%m-%d")

        file_count = 0
        for k, file in enumerate(self.file_list):
            date = file['date'].strftime("%Y-%m-%d")
            diff_date = datetime.datetime.strptime(
                today, "%Y-%m-%d") - datetime.datetime.strptime(date, "%Y-%m-%d")

            exclude_match = False
            for exclude in exclude_dir:
                if file['full_filename'].count(exclude) > 0:  # not match
                    exclude_match = True
                if exclude_match is True:
                    break

            if exclude_match is False:
                is_append = False
                if self.upload_target_date == "today":
                    if diff_date.days <= 1:
                        is_append = True
                elif self.upload_target_date == "all":
                    is_append = True
                elif self.upload_target_date == date:
                    is_append = True

                if is_append:
                    self.upload_target_files.append(file['full_filename'])
                    print(f"[{file_count:^3}] [{self.upload_target_date:^8}] :: {file['full_filename']:40}  "
                          f"{file['size']:10} {file['date']} ({diff_date.days})")
                    file_count += 1

    def compress_zip(self):
        zip = zipfile.ZipFile(f'{self.upload_filename}', 'w')
        spinner = Halo(text=f"Archive files - {self.upload_filename}\n", spinner='dots')
        spinner.start()
        for filename in self.upload_target_files:
            try:
                print(f" -> {filename}")
                zip.write(filename,
                          os.path.relpath(filename),
                          compress_type=zipfile.ZIP_DEFLATED)
            except Exception as e:
                cprint(f"[ERR] {e}")
                spinner.fail(f'Fail {e}')
        spinner.succeed(f"Archive Done - {self.upload_filename}, {get_file_info(self.upload_filename).get('size')}")

    def upload(self):
        pass

    def _prepare(self):

        if self.upload_filename is None:
            self.set_upload_filename()

    def set_upload_filename(self, name=None):
        if name is None:
            name = input("Enter your prep-name: ")
        self.upload_filename = f"ICON2-{name}-{base.get_public_ipaddr()}-{converter.todaydate('file')}.zip"


def banner():
    print("=" * 57)
    print(' _____ _____ _____ ____  _____ _____    __    _____ _____')
    print('|   __|   __|   | |    \|     |   __|  |  |  |     |   __|')
    print('|__   |   __| | | |  |  | | | |   __|  |  |__|  |  |  |  |')
    print('|_____|_____|_|___|____/|_|_|_|_____|  |_____|_____|_____|')
    print("")
    print(f'                                       version: {version}')
    print("\t\t\t\t\t   by JINWOO")
    print("=" * 57)


if __name__ == '__main__':
    enc_keys = {
        "encode_key": b"ZhiS-yXbkk_KPbGkqIw85FX2aHRhSBrG-yVOQiTiZeg=",
        "aawwss_text": b"gAAAAABeIXCBukgBLiLfCPt8xD-zWLHxc6OfMfmZjsR02mY0CGYA_3mdevoURb_BRs_19nQdUEDNEpNag9xawP9m7Ug1CWNKDdha5_2J36AL9CG-I9"
                       b"-9wHaUGD1GUuDfdxitfLcebKMtcy9VGDqr8A8vrYLeEb8NDQ== ",
        "aawwss_env": b"gAAAAABeIXy9YdGvJCmmxbBTnsbb-APE1RCKiYvciOYXMU-EXrXhjlvg6XJgb38MyY0cRzMM3TfiIyXrNbDTntA7R9cY_"
                      b"EWuSuCcdK9LlnKVuL2qc_ITkVMQ5lgl-gNcgKCrqQS7xMTB"
    }
    parser = get_parser()
    args = parser.parse_args()

    exclude_dir = [".score_data", ".storage", ".git"]
    banner()
    print(args)
    cfg = CFG()
    if args.log_dir is None and base.is_docker():
        log_dir = f"{cfg.config.get('BASE_DIR', '/goloop')}/logs"
        network = cfg.config.get('SERVICE')
    else:
        log_dir = args.log_dir
        network = args.network

    if args.exclude_dir is None:
        exclude_dir = [".score_data", ".storage", ".git"]

    if args.name:
        name = args.name
    else:
        name = input("Enter your prep-name: ")

    upload_filename = f"ICON2-{name}-{base.get_public_ipaddr()}-{converter.todaydate('file')}.zip"

    try:
        SendLog(
            verbose=args.verbose,
            log_dir=log_dir,
            upload_filename=upload_filename,
            upload_target_date=args.target_date,
            network=args.network,
            enc_keys=enc_keys,
            exclude_dir=exclude_dir,
            region=args.region
        ).run()
    except KeyboardInterrupt:
        cprint("\nKeyboardInterrupt", "green")
        pass
    finally:
        if upload_filename is not None and os.path.isfile(upload_filename):
            print(f'Remove temporary zip file -> {upload_filename}')
            os.remove(upload_filename)
