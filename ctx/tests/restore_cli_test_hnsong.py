#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import append_parent_path
import os
from config.configure import Configure as CFG
from common import converter, output, base
from common.output import cprint, converter
from common.converter import region_info     ### regeion config
# from manager import restore_hnsong as restore
from manager.restore_v3 import Restore

import argparse

print(converter.todaydate("file"))
print(converter.todaydate())

# local_dir_info = {}

# res = dict(shutil.disk_usage("/Users/jinwoo/work/ICON2_TEST"))
# print(res.usage)∏

base.disable_ssl_warnings()

cfg = CFG()
config = cfg.config
output.classdump(cfg.config)
print(cfg.config)

exit()
icon2_config = config['settings']['icon2']
env_config = config['settings']['env']
# compose_env_config = config['settings']['env']['COMPOSE_ENV']

### Goloop DB PATH
if icon2_config.get('GOLOOP_NODE_DIR') :
    db_path = icon2_config['GOLOOP_NODE_DIR']
else :
    default_db_path = 'data'
    # base_dir = compose_env_config['BASE_DIR']
    base_dir = env_config['BASE_DIR']
    db_path = os.path.join(base_dir, default_db_path)

### Restore Options
### network  =  MainNet | SejongNet ....
# network = env_config['SERVICE']  if env_config.get('SERVICE') else compose_env_config['SERVICE']
# restore_path = env_config['RESTORE_PATH']  if env_config.get('RESTORE_PATH') else compose_env_config['RESTORE_PATH']
# dl_force = env_config['DOWNLOAD_FORCE']  if env_config.get('DOWNLOAD_FORCE') else compose_env_config['DOWNLOAD_FORCE']
# download_tool = env_config['DOWNLOAD_TOOL']  if env_config.get('DOWNLOAD_TOOL') else compose_env_config['DOWNLOAD_TOOL']
# download_url = env_config['DOWNLOAD_URL']  if env_config.get('DOWNLOAD_URL') else compose_env_config['DOWNLOAD_URL']
# download_url_type = env_config['DOWNLOAD_URL_TYPE']  if env_config.get('DOWNLOAD_URL_TYPE') else compose_env_config['DOWNLOAD_URL_TYPE']
network = env_config['SERVICE']
restore_path = env_config['RESTORE_PATH']
dl_force = env_config['DOWNLOAD_FORCE']
download_tool = env_config['DOWNLOAD_TOOL']
download_url = env_config['DOWNLOAD_URL']
download_url_type = env_config['DOWNLOAD_URL_TYPE']

Restore(
    db_path=db_path,
    network=network,
    download_path=restore_path,
    download_force=dl_force,
    download_url=download_url,
    download_tool=download_tool,
    download_url_type=download_url_type
)

exit()

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
