#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import append_parent_path
from config.configure import Configure as CFG
from manager.file_indexing import FileIndexer
import argparse
import requests
from common import output, converter, base

cfg = CFG()

if base.is_docker():
    data_dir = f"{cfg.config.get('BASE_DIR', '/goloop')}/data"
    checksum_file = f"{data_dir}/restore/checksum.json"


def download_write_file(url, path=None):
    if url:
        local_filename = url.split('/')[-1]
        if path:
            full_path_filename = f"{path}/{local_filename}"
        else:
            full_path_filename = local_filename
        with requests.get(url) as r:
            r.raise_for_status()
            output.cprint(f"{output.write_file(filename=full_path_filename, data=r.text)}")
    else:
        raise Exception(f"download_write_file() Invalid url {url}")


def get_parser():
    parser = argparse.ArgumentParser(
        description='recursive file indexing',
        fromfile_prefix_chars='@'
    )

    sub_parser = parser.add_subparsers(dest='command')
    sub_parser.add_parser('check')
    sub_parser.add_parser('index')
    sub_parser.default = "check"

    parser.add_argument('-d', '--dir', help='destination directory name (default: ./)',
                        default=data_dir)

    parser.add_argument('-p', '--prefix', help=f'prefix name (e.g. http://PREFIX/)',
                        default=f"")

    parser.add_argument('-m', '--check-method', help=f'how to check the method,',
                        choices=["hash", "size"],
                        default=f"hash")

    parser.add_argument('-v', '--verbose', action='count', help=f'verbose mode. view level', default=0)
    parser.add_argument('-c', '--checksum-file', help=f'checksum filename', default="checksum.json")
    parser.add_argument('-o', '--output-path', help=f'output path', default="./")

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
        res = FileIndexer(
            base_dir=args.dir,
            debug=debug,
            check_method=args.check_method,
            prefix=args.prefix,
            checksum_filename=args.checksum_file
        ).check()
        if res.get("status"):
            print(f"Check result: {res['status']}")
        # for status, result in res.items():
        #     if isinstance(result, dict):
        #         for key, values in result.items():
        #             print(f"[{status}], [{key}], [{values}]")


if __name__ == "__main__":
    main()
