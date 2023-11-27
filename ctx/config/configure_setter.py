#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.configure import Configure as CFG
from common.icon2 import WalletLoader
from common.output import is_file, write_file, write_json, write_yaml, dump
from manager.restore_v3 import Restore
from pawnlib.resource import net


class ConfigureSetter:
    def __init__(self, ):
        self.cfg = CFG(use_file=False)
        self.config = self.cfg.config
        self.base_dir = self.config.get('BASE_DIR')
        self.config_dir = f"{self.base_dir}/config"

    def make_base_dir(self, ):
        for node_dir in [self.base_dir,
                         f"{self.base_dir}/config",
                         f"{self.config['GOLOOP_NODE_DIR']}",
                         f"{self.base_dir}/logs"
                         ]:
            if not os.path.exists(node_dir):
                os.mkdir(node_dir)

    def delete_sock(self, ):
        sock_dir = f"{self.base_dir}/data"
        _cli_sock = f"{sock_dir}/cli.sock"
        _ee_sock = f"{sock_dir}/ee.sock"
        if is_file(_cli_sock):
            os.remove(_cli_sock)
        if is_file(_ee_sock):
            os.remove(_ee_sock)

    def create_key(self, ):
        self.cfg.logger.info(f"Start {sys._getframe().f_code.co_name}")
        if not os.path.exists(self.base_dir):
            self.make_base_dir()
        keysecret_passwd = self.config.get('KEY_PASSWORD')
        keysecret_filename = self.config.get('GOLOOP_KEY_SECRET', '/goloop/config/keysecret')
        keystore_filename = self.config.get('KEY_STORE_FILENAME', None)

        if keystore_filename is None:
            keystore_filename = self.config.get('GOLOOP_KEY_STORE', 'keystore.json').split('/')[-1]

        if is_file(f"{self.config_dir}/{keystore_filename}") is False or self.config.get('KEY_RESET', False) is True:
            if self.cfg.config.get('IS_AUTOGEN_CERT') is True:
                wallet = WalletLoader(f"{self.config_dir}/{keystore_filename}", keysecret_passwd, keysecret_filename, force_sync=True)
                wallet.create_wallet()
                write_file(f'{keysecret_filename}', keysecret_passwd)
                self.cfg.logger.info(f"Create a keystore, filename={keystore_filename}, address={wallet.wallet.get_address()}")
        else:
            write_file(f'{keysecret_filename}', keysecret_passwd)
            self.cfg.logger.info(write_file(f'{keysecret_filename}', keysecret_passwd))
            wallet = WalletLoader(f"{self.config_dir}/{keystore_filename}", keysecret_passwd, keysecret_filename)
            wallet.get_wallet()

            self.cfg.logger.info(f"Already keystore file - {keystore_filename}")

    def create_genesis_json(self, ):
        self.cfg.logger.info(f"Start {sys._getframe().f_code.co_name}")
        rs = write_json(
            f"{self.config.get('GENESIS_JSON', '/goloop/config/genesis.json')}",
            self.config.get('GENESIS')
        )
        self.cfg.logger.info(f"{rs}")

    def create_gs_zip(self, ):
        self.cfg.logger.info(f"Start {sys._getframe().f_code.co_name}")
        genesis_file = f'{self.config.get("CONFIG_URL")}/{self.config.get("SERVICE")}/icon_genesis.zip'
        res = requests.get(genesis_file)
        if res.status_code == 200:
            rs = write_file(
                f"{self.config.get('GENESIS_STORAGE', '/goloop/config/icon_genesis.zip')}",
                res.content,
                option='wb'
            )
            self.cfg.logger.info(f"{rs}")
        else:
            self.cfg.logger.error(f"[ERROR] Cant download the genesis_file ({genesis_file}). status_code={res.status_code}")

    def create_icon_config(self, ):
        self.cfg.logger.info(f"Start {sys._getframe().f_code.co_name}")
        if self.config.get('IISS'):
            rs = write_json(
                f"{self.config.get('IISS_JSON', f'/goloop/icon_config.json')}",
                self.config.get('IISS')
            )
            self.cfg.logger.info(f"{rs}")

    def create_yaml_file(self, file_name=None):
        self.cfg.logger.info(f"Start {sys._getframe().f_code.co_name}")
        if file_name is None:
            file_name = f"{os.path.join(self.base_dir, self.config.get('CONFIG_LOCAL_FILE', 'configure.yml'))}"
        rs = write_yaml(
            file_name,
            self.config
        )
        self.cfg.logger.info(f"{rs}")

    def create_env_file(self, file_name: str = '.env'):
        file_name = f"{os.path.join(self.base_dir, file_name)}"
        self.cfg.logger.info(f"Start {sys._getframe().f_code.co_name}")
        with open(file_name, 'w') as env:
            for key, val in self.config.items():
                if key in ["KEY_PASSWORD", "KEY_SECRET"]:
                    continue
                if isinstance(val, dict) or isinstance(val, list):
                    continue
                if val is not None:
                    env.write(f"{key}={val}\n")

    def create_db(self, ):
        self.cfg.logger.info(f"Start {sys._getframe().f_code.co_name}")
        self.cfg.logger.info(f"[RESTORE] "
                             f"FASTEST_START = {self.config.get('FASTEST_START')}"
                             )
        if self.config.get('FASTEST_START') is True:
            self.cfg.logger.info("[RESTORE] DOWNLOAD from ICON DB")
            self.downloader()

        else:
            self.cfg.logger.info("[PASS] Ignore DB download")

    def downloader(self, ):
        base_dir = self.config.get('BASE_DIR')

        # Goloop DB PATH
        if self.config.get('GOLOOP_NODE_DIR'):
            db_path = self.config['GOLOOP_NODE_DIR']
        else:
            default_db_path = 'data'
            db_path = os.path.join(base_dir, default_db_path)

        service = self.config['SERVICE']
        restore_path = f"{db_path}/{self.config['RESTORE_PATH']}"
        download_force = self.config['DOWNLOAD_FORCE']
        download_tool = self.config['DOWNLOAD_TOOL']

        download_url = self.config['DOWNLOAD_URL']
        download_url_type = self.config['DOWNLOAD_URL_TYPE']
        download_option = self.config.get('DOWNLOAD_OPTION', None)

        Restore(
            db_path=db_path,
            network=service,
            download_path=restore_path,
            download_force=download_force,
            download_url=download_url,
            download_tool=download_tool,
            download_url_type=download_url_type,
            download_option=download_option,
        )

    def check_seed_servers(self):
        seeds = self.config.get('SEEDS').split(',')
        exception_messages = []
        for seed in seeds:
            if not net.check_port(seed):
                exception_messages.append(seed)
                self.cfg.handle_value_error(f"Failed to connect to the server. seed={seed}")
        if len(exception_messages) >= len(seeds) > 0:
            self.cfg.handle_value_error(f"Cannot connect to Seed Servers 👉 {exception_messages}")

    def check_role(self):
        allows_roles = [0, 1, 3]
        if self.config.get('ROLE') not in allows_roles:
            self.cfg.handle_value_error(f"Invalid ROLE, role={self.config.get('ROLE')}, allows={allows_roles}")

    def validate_environment(self):
        mandatory_env_keys = ["KEY_PASSWORD"]
        for env_key in mandatory_env_keys:
            env_value = os.getenv(env_key)
            self.cfg.logger.debug(f"Validate environment {env_key}={env_value}")
            if not os.getenv(env_key):
                # self.logger.error(f"There is no password. Requires '{key}' environment.")
                self.cfg.handle_value_error(f"There is no '{env_key}'. Requires '{env_key}' environment. {env_key}='{env_value}'")

    def check_server_environment_prepare(self):
        self.check_seed_servers()
        self.check_role()
        self.validate_environment()
        # TODO
        # check keystore file
        # sys.exit(-127)

    def run(self, ):
        dump(self.config)
        self.config['BASE_DIR'] = os.getcwd()
        self.config['CONFIG_LOCAL_FILE'] = f'configure.yml'
        self.config['GOLOOP_KEY_SECRET'] = f'keysecret'
        self.config['GOLOOP_KEY_STORE'] = f'keystore.json'
        self.config['GENESIS_JSON'] = f'genesis.json'
        self.config['GENESIS_STORAGE'] = f'gs.zip'
        self.config['IISS_JSON'] = f'icon_config.json'
        self.create_yaml_file()
        self.create_env_file('.env')
        self.make_base_dir()
        self.create_key()
        self.create_genesis_json()
        self.create_gs_zip()
        self.create_icon_config()


if __name__ == '__main__':
    CS = ConfigureSetter()
    CS.run()
