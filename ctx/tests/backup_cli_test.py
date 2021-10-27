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
from manager import backup
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
        "-bk",
        "--backup_path",
        help=f"Backup Path",
        default=f"{kwargs.get('backup_dir')}"
    )
    parser.add_argument(
        "-r",
        "--region",
        type=str,
        help=f"Region",
        choices=["kr", "jp", "va", "hk",
                 "sg", "mb", "ff", "sy"],
        default="kr"
    )
    parser.add_argument("-p", "--profile", default=None)
    parser.add_argument('-t', '--upload-type', type=str,
                        help=f'upload type', choices=["single", "multi"], default="multi")
    parser.add_argument(
        "-n",
        "--network",
        type=str,
        help=f"Network name",
        choices=["MainNet", "TestNet"],
        default="MainNet",
    )
    return parser.parse_args()

def main():
    docker_path = "/app/goloop"
    db_dir = "/app/goloop/data"
    backup_dir = f"/app/goloop/data"
    send_url = (
        "https://hooks.slack.com/services/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"
    )

    args = parse_args(db_dir=db_dir,backup_dir=backup_dir)
    if args.db_path:
        db_path = args.db_path
    else:
        db_path = db_dir
    if args.backup_path:
        backup_path = args.backup_path
    else:
        backup_path = backup_dir

    backup.Backup(
        core_version='core2',    ### default= core2 , choice [core1] or [core2] 
        db_path=args.db_path,
        backup_path=args.backup_path,
        network=args.network,
        send_url=send_url,
        region=args.region,
        docker_path=docker_path,
        docker_file='docker-compose.yml',
        # db_path="/Users/jinwoo/work/ICON2_TEST",
        # profile="upload_test"
    )

if __name__ == "__main__":
    main()
