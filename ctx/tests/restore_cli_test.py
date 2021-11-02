#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

parent_dir = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
sys.path.append(parent_dir)
sys.path.append(parent_dir+"/..")

from config.configure import Configure
from common import converter, output, base
from common.output import cprint, converter

from common.converter import region_info     ### regeion config
from manager import restore

import argparse

print(converter.todaydate("file"))
print(converter.todaydate())

# local_dir_info = {}

# res = dict(shutil.disk_usage("/Users/jinwoo/work/ICON2_TEST"))
# print(res.usage)∏

base.disable_ssl_warnings()

def parse_args(**kwargs):
    parser = argparse.ArgumentParser(description="leveldb Backup")
    parser.add_argument(
        "-db",
        "--db_path",
        help=f"DB Path",
        default=f"{kwargs.get('db_dir')}"
    )
    parser.add_argument(
        "-r",
        "--region",
        type=str,
        help=f"Region",
        choices=["kr", "jp", "va", "hk",
                 "sg", "mb", "ff", "sy"],
        default=None
    )
    parser.add_argument("-p", "--profile", default=None)
    parser.add_argument('-t', '--download-type', type=str,
                        help=f'download type', choices=["single", "multi"], default="multi")
    parser.add_argument(
        "-n",
        "--network",
        type=str,
        help=f"Network name",
        choices=["MainNet", "TestNet"],
        default="MainNet",
    )
    parser.add_argument("-v", "--verbose", default=None)

    return parser.parse_args()

def main():
    docker_path = "/app/goloop"
    db_dir = "/app/goloop/data"
    send_url = (
        ""
    )
    region = "kr"

    args = parse_args(db_dir=db_dir,region=region)
    if args.db_path is None:
        db_path = db_dir
    else:
        db_path = args.db_path

    if args.region is None:
        region = region
    else:
        region = args.region


    print('hnsong')
    restore.Restore(
        db_path=db_path,
        network=args.network,
        send_url=send_url,
        region=region
        # db_path="/Users/jinwoo/work/ICON2_TEST",
        # profile="upload_test"
    )

if __name__ == "__main__":
    main()
