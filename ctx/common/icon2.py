#!/usr/bin/env python3
#-*- coding: utf-8 -*-


import os
import requests
import shutil

from iconsdk.wallet.wallet import KeyWallet
from iconsdk.wallet import wallet
from common import output, converter
from asn1crypto import keys
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

import hashlib
from config.configure import Configure as CFG


def generate_wallet(file:str, password:str) -> str:
    if os.path.exists(file):
        wallet = get_wallet(file, password)
    else:
        wallet = KeyWallet.create()
        wallet.store(file, password) # throw exception if having an error.
    return wallet.get_address()


def get_wallet(file:str, password:str) -> wallet:
    wallet = KeyWallet.load(file, password)
    return wallet


def get_preps(endpoint):
    payload = {
        "id": 1234,
        "jsonrpc": "2.0",
        "method": "icx_call",
        "params": {
            "to": "cx0000000000000000000000000000000000000000",
            "dataType": "call",
            "data": {
                "method": "getPReps",
                "params": {}
            }
        }
    }
    try:
        res = requests.post(
            url=f"{endpoint}/api/v3",
            json=payload
        )
        if res.status_code == 200:
            return res.json()
        else:
            return {"error": res.status_code}
    except Exception as e:
        return {"error": e}


def get_inspect(endpoint, cid):
    try:
        res = requests.get(
            url=f"{endpoint}/admin/chain/{cid}"
        )
        if res.status_code == 200:
            return_res = res.json()
            return return_res[0] if isinstance(return_res, list) else return_res
        else:
            return {"error": res.status_code}
    except Exception as e:
        return {"error": e}


class WalletLoader:
    def __init__(self, filename, password, keysecret_filename, default_path=None, force_sync=False, is_logging=True, debug=False):
        self.filename = filename
        self.password = password
        self.keysecret_filename = keysecret_filename
        self.default_path = default_path
        self.force_sync = force_sync
        self.is_logging = is_logging
        self.debug = debug
        self.keystore_type = ""
        self.filename_info = {}
        self.wallet = None

        self.cfg = None

        if self.is_logging:
            self.cfg = CFG()

        self.guess_proc()
        self.sync_keysecret_file()

        # if self.keystore_type == "der" or self.keystore_type == "pem":
        #     self.from_prikey_file()

    def print_logging(self, message=None, color="green"):
        if self.cfg:
            if color == "red":
                self.cfg.logger.error(f"[WALLET] {message}")
            else:
                self.cfg.logger.info(f"[WALLET] {message}")
        else:
            output.cprint(message, color)

    def sync_keysecret_file(self):
        if self.force_sync and output.is_file(self.keysecret_filename):
            keysecret = output.open_file(self.keysecret_filename)
            if keysecret != self.password:
                self.print_logging(f"Sync password to a '{self.keysecret_filename}' file", "green")
                output.write_file(self.keysecret_filename, self.password)

    def guess_proc(self):
        self.guess_path()
        self.guess_keystore_type()
        self.print_logging(f"Keystore file: {self.filename}, File type: {self.keystore_type}\n", "green")

    def guess_keystore_type(self):
        self.keystore_type = ""
        if output.is_file(self.filename):
            if output.is_json(self.filename):
                self.keystore_type = "json"
            elif output.is_binary_string(self.filename):
                self.keystore_type = "der"
            else:
                self.keystore_type = "pem"
        else:
            self.print_logging(f"[Error] File not found - {self.filename}", "red")

    def guess_path(self):
        self.filename_info = output.get_file_path(self.filename)
        if not self.filename_info.get('base_dir', None) and self.default_path:
            self.filename = f"{self.default_path}/{self.filename}"
        self.filename_info['converted_file'] = f"{self.filename_info.get('dirname')}/{self.filename_info.get('file').replace(self.filename_info.get('extension'), '.json')}"

    def create_wallet(self, filename=None, password=None):
        if filename is None:
            filename = self.filename

        if password is None:
            password = self.password

        if self.debug:
            self.print_logging(f"filename={filename}, password={password}, keysecret={self.keysecret_filename}", "white")

        for dest_file in [filename, self.keysecret_filename]:
            if self.force_sync and output.is_file(dest_file):
                self.print_logging(f"Remove the '{dest_file}' file", "red") if self.debug else False
                os.remove(dest_file)
            else:
                output.check_file_overwrite(dest_file)
            # check_overwrite(self.keysecret_filename)

        if self.wallet is None:
            self.wallet = KeyWallet.create()

        self.print_logging(f"Create a Keystore file", "green")
        self.wallet.store(filename, password)  # throw exception if having an error.
        key_json = output.open_json(filename)
        self.print_logging(f"Write to file => {filename}", "green")
        output.print_json(key_json, indent=4)

        self.print_logging(f"Write to file => {self.keysecret_filename}", "green")

        output.write_file(self.keysecret_filename, password)
        self.print_logging(f"Stored filename={filename}, address={self.wallet.get_address()}, size={converter.get_size(filename)}", "yellow")

    def get_wallet(self):
        if self.keystore_type == "json":
            if output.is_file(self.keysecret_filename):
                keysecret = output.open_file(self.keysecret_filename)
                if keysecret != self.password:
                    # self.print_logging(f"keysecret({keysecret}) and password({self.password}) are different", "red")
                    self.print_logging(f"keysecret and password are different", "red")
            keystore = output.open_file(self.filename)
            self.wallet = KeyWallet.load(self.filename, self.password)
            if len(keystore) != 0:
                if u"\ufeff" in keystore:
                    self.print_logging(f"[WARN] Found UTF-8 BOM in the your Keystore file. It will be converted to standard JSON.", "white")
                    backup_file = shutil.move(self.filename, f"{self.filename}_backup")
                    self.print_logging(f"[WARN] Backup original file - {backup_file}", "white")
                    if backup_file and output.is_file(f"{self.filename}_backup"):
                        self.wallet.store(f"{self.filename}", self.password)
                    if output.is_file(self.filename):
                        self.print_logging(f"[OK] Successfully convert - {self.filename}", "white")
        else:
            self.wallet = self.from_prikey_file()

        if self.wallet:
            self.print_logging(f"Successfully loaded Keystore file({self.keystore_type}), address={self.wallet.get_address()}, file={self.filename}", "white")
            return self.wallet

    def convert_keystore(self):
        if self.keystore_type == "json":
            self.print_logging(f"Already converted keystore file", "red")
            return None

        if not output.is_file(self.filename):
            self.print_logging(f"[ERROR] File not found. {self.filename}", "red")
            return None

        self.get_wallet()

        if self.filename_info.get('converted_file'):
            self.print_logging(f"Convert '{self.filename}' to '{self.filename_info['converted_file']}'")
            self.create_wallet(filename=self.filename_info['converted_file'])
            return self.wallet

    def from_prikey_file(self):
        encoded_password = None
        if isinstance(self.password, str):
            encoded_password = self.password.encode()

        with open(self.filename, "rb") as file:
            private_bytes = file.read()
        try:
            if output.is_binary_string(self.filename):
                key_file_type = "der"
                load_private = serialization \
                    .load_der_private_key(private_bytes,
                                          encoded_password,
                                          default_backend())
            else:
                key_file_type = "pem"
                load_private = serialization \
                    .load_pem_private_key(private_bytes,
                                          encoded_password,
                                          default_backend())
        except Exception as e:
            raise ValueError(f"[WALLET] Invalid Password or Certificate load Failure - {e}")

        key_info = keys.PrivateKeyInfo.load(
            load_private.private_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
        )

        private_key_native = key_info['private_key'].native['private_key']
        private_key_bytes = converter.long_to_bytes(private_key_native)

        public_key = load_private.public_key()
        public_key_info = keys.PublicKeyInfo.load(
            public_key.public_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PublicFormat['SubjectPublicKeyInfo']
            )
        )

        public_key_native = public_key_info['public_key'].native
        hash_pub = hashlib.sha3_256(public_key_native[1:]).hexdigest()
        address = f"hx{hash_pub[-40:]}"
        self.print_logging(f"hx address from {key_file_type} file: {address}")

        self.wallet = KeyWallet.load(private_key_bytes)
        self.print_logging(f"hx address from ICON wallet, {self.wallet.get_address()}")

        if address != self.wallet.get_address():
            raise Exception("[WALLET] Something wrong, Miss match address")
        else:
            return self.wallet
