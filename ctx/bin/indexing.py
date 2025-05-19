#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import append_parent_path
# from config.configure import Configure as CFG
from manager.file_indexing import FileIndexer
import argparse
import requests
from common import converter
from pawnlib import output
from pawnlib.config import pawn
import os


def is_docker():
    return converter.str2bool(os.environ.get("IS_DOCKER", False))

if is_docker():
    data_dir = f"{os.getenv('BASE_DIR', '/goloop')}/data"
    checksum_file = f"{data_dir}/restore/checksum.json"
    output_dir = f"{data_dir}/restore"



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

    parser.add_argument('-d', '--dir', help=f'destination directory name (default: {data_dir})',
                        default=data_dir)
    parser.add_argument('-p', '--prefix', help='prefix name (e.g. http://PREFIX/)',
                        default="")

    parser.add_argument('-m', '--check-method', help='how to check the method,',
                        choices=["hash", "size"],
                        default="hash")

    parser.add_argument('--exclude-files', action='append', help='List of files to exclude', default=["restore"])

    parser.add_argument('-v', '--verbose', action='count', help='verbose mode. view level', default=0)
    parser.add_argument('-c', '--checksum-file', help='checksum filename', default="checksum.json")
    parser.add_argument('-o', '--output-path', help=f'output path (default: {output_dir}) ', default=output_dir)

    return parser.parse_args()


def main():
    args = get_parser()
    if args.verbose > 0:
        debug = True
    else:
        debug = False

    pawn.console.log(args)
    pawn.console.log(f"checksum_file={args.checksum_file}")

    file_indexer = FileIndexer(
        base_dir=args.dir,
        debug=debug,
        check_method=args.check_method,
        prefix=args.prefix,
        checksum_filename=args.checksum_file,
        output_path=args.output_path,
        exclude_files=args.exclude_files,
    )

    if args.command == "index":
        file_indexer.run()
    elif args.command == "check":
        res = file_indexer.check()
        pawn.console.log(res)
        if res.get("status"):
            pawn.console.log(f"Check result: {res['status']}")


if __name__ == "__main__":
    main()
