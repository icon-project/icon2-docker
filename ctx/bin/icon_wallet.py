#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import append_parent_path
from config.configure import Configure as CFG
from common import output, converter, base, icon2
import argparse
import sys
import os


def main():
    cfg = CFG()
    cfg.get_config(True)
    cfg_config = cfg.config

    parser = argparse.ArgumentParser(prog='icon_wallet')
    parser.add_argument('command', choices=["create", "get", "convert"])
    parser.add_argument('-p', '--password', type=str, help=f'keystore password', default=None)
    parser.add_argument('-f', '--filename', type=str, help=f'keystore filename', default="keystore_test.json")
    parser.add_argument('-v', '--verbose', action='count', help=f'verbose mode ', default=0)
    parser.add_argument('-fs', '--force-sync', metavar='True/False', type=converter.str2bool,
                        help=f'Synchronize password and keysecret ', default=False)

    args = parser.parse_args()

    dirname, file_name = os.path.split(args.filename)

    if base.is_docker() and dirname == "":
        config_dir = f"{cfg.config['settings']['env'].get('BASE_DIR', '/goloop')}/config"
        keystore_filename = f"{config_dir}/{args.filename}"
    else:
        config_dir = None
        keystore_filename = args.filename

    if args.command != "create" and not output.is_file(keystore_filename):
        output.cprint(f"[ERROR] File not found, {keystore_filename}", "red")
        sys.exit(127)

    if args.password is None:
        args.password = output.colored_input("Input your keystore password:", password=True)
        if args.password is None:
            output.cprint("[ERROR] need a password", "red")
            sys.exit(127)

    keysecret_filename = cfg_config.get('GOLOOP_KEY_SECRET', '/goloop/config/keysecret')

    if args.verbose > 0:
        debug = True
        output.cprint(f"\nArguments = {args}")
    else:
        debug = False

    wallet_loader = icon2.WalletLoader(
        filename=args.filename,
        password=args.password,
        keysecret_filename=keysecret_filename,
        force_sync=args.force_sync,
        default_path=config_dir,
        debug=debug,
        is_logging=False
    )

    if args.command == "create":
        wallet_loader.create_wallet()

    elif args.command == "get":
        output.cprint(f"Load Keystore file", "green")
        wallet_loader.get_wallet()

    elif args.command == "convert":
        output.cprint(f"Convert file", "green")
        wallet = wallet_loader.convert_keystore()
        if wallet:
            print(wallet.get_address())


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        output.cprint("\n\nKeyboardInterrupt", "red")
