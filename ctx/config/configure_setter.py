#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import yaml
import time
import requests

from termcolor import cprint

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.configure import Configure as CFG
from common.icon2 import WalletLoader
from common.output import is_file,  write_file, write_json, write_yaml, dump
from manager.restore_v3 import Restore


class ConfigureSetter:
    def __init__(self, ):
        self.cfg = CFG(use_file=False)
        self.config = self.cfg.config
        self.base_dir = self.config['settings']['env'].get('BASE_DIR')
        self.config_dir = f"{self.base_dir}/config"

    def make_base_dir(self, ):
        for node_dir in [self.base_dir, f"{self.base_dir}/config", f"{self.base_dir}/data", f"{self.base_dir}/logs"]:
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
        keysecret_passwd = self.config['settings']['env'].get('KEY_PASSWORD', self.config['settings']['env']['COMPOSE_ENV'].get('KEY_PASSWORD'))
        keysecret_filename = self.config['settings']['icon2'].get('GOLOOP_KEY_SECRET', '/goloop/config/keysecret')
        keystore_filename = self.config['settings']['env'].get('KEY_STORE_FILENAME', None)

        if keystore_filename is None:
            keystore_filename = self.config['settings']['icon2'].get('GOLOOP_KEY_STORE', 'keystore.json').split('/')[-1]

        if is_file(f"{self.config_dir}/{keystore_filename}") is False or self.config['settings']['env'].get('KEY_RESET', False) is True:
            if self.cfg.config['settings']['env'].get('IS_AUTOGEN_CERT') is True:
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
            f"{self.config['settings'].get('genesis_json', '/goloop/config/genesis.json')}",
            self.config['settings'].get('genesis')
        )
        self.cfg.logger.info(f"{rs}")

    def create_gs_zip(self, ):
        self.cfg.logger.info(f"Start {sys._getframe().f_code.co_name}")
        genesis_file = f'{self.config["settings"]["env"]["CONFIG_URL"]}/{self.config["settings"]["env"]["SERVICE"]}/icon_genesis.zip'
        res = requests.get(genesis_file)
        if res.status_code == 200:
            rs = write_file(
                f"{self.config['settings'].get('genesis_storage', '/goloop/config/icon_genesis.zip')}",
                res.content,
                option='wb'
            )
            self.cfg.logger.info(f"{rs}")
        else:
            self.cfg.logger.error(f"API status code is {res.status_code}. ({genesis_file})")

    def create_icon_config(self, ):
        self.cfg.logger.info(f"Start {sys._getframe().f_code.co_name}")
        if self.config['settings'].get('iiss'):
            rs = write_json(
                f"{self.config['settings'].get('iiss_json', f'/goloop/icon_config.json')}",
                self.config['settings'].get('iiss')
            )
            self.cfg.logger.info(f"{rs}")

    def create_yaml_file(self, file_name=None):
        self.cfg.logger.info(f"Start {sys._getframe().f_code.co_name}")
        if file_name is None:
            file_name = f"{os.path.join(self.base_dir, self.config['settings']['env'].get('CONFIG_LOCAL_FILE', 'configure.yml'))}"
        rs = write_yaml(
            file_name,
            self.config
        )
        self.cfg.logger.info(f"{rs}")

    def create_env_file(self, file_name: str='.env'):
        file_name = f"{os.path.join(self.base_dir, file_name)}"
        self.cfg.logger.info(f"Start {sys._getframe().f_code.co_name}")
        with open(file_name, 'w') as env:
            for key, val in self.config['settings']['env'].items():
                if key == 'COMPOSE_ENV':
                    continue
                env.write(f"{key}=\"{val}\"\n")
            for key, val in self.config['settings']['icon2'].items():
                env.write(f"{key}=\"{val}\"\n")

    def create_db(self, ):
        self.cfg.logger.info(f"Start {sys._getframe().f_code.co_name}")
        time.sleep(self.config['settings']['mig'].get('MIG_REST_TIME', 5))
        self.cfg.logger.info(f"[RESTORE] "
                             f"FASTEST_START = {self.config['settings']['env'].get('FASTEST_START')}, "
                             f"MIG_DB = {self.config['settings']['mig'].get('MIG_DB')}"
                             )
        if self.config['settings']['env'].get('FASTEST_START') is True:
            if self.config['settings']['mig'].get('MIG_DB') is True:
                self.cfg.logger.info(f"[RESTORE] DOWNLOAD from Migration Stage2 DB")
            else:
                self.cfg.logger.info(f"[RESTORE] DOWNLOAD from ICON2 DB")
            self.downloader()

        else:
            self.cfg.logger.info(f"[PASS] Ignore DB download")

    def downloader(self, ):
        icon2_config = self.config['settings']['icon2']
        env_config = self.config['settings']['env']
        compose_env_config = self.config['settings']['env']['COMPOSE_ENV']

        base_dir = compose_env_config['BASE_DIR']

        # Goloop DB PATH
        if icon2_config.get('GOLOOP_NODE_DIR') :
            db_path = icon2_config['GOLOOP_NODE_DIR']
        else:
            default_db_path = 'data'
            db_path = os.path.join(base_dir, default_db_path)

        service = env_config['SERVICE'] if env_config.get('SERVICE') else compose_env_config['SERVICE']
        restore_path = f"{db_path}/{env_config['RESTORE_PATH'] if env_config.get('RESTORE_PATH') else compose_env_config['RESTORE_PATH']}"
        download_force = env_config['DOWNLOAD_FORCE'] if env_config.get('DOWNLOAD_FORCE') else compose_env_config['DOWNLOAD_FORCE']
        download_tool = env_config['DOWNLOAD_TOOL'] if env_config.get('DOWNLOAD_TOOL') else compose_env_config['DOWNLOAD_TOOL']

        download_url = env_config['DOWNLOAD_URL'] if env_config.get('DOWNLOAD_URL') else compose_env_config['DOWNLOAD_URL']
        download_url_type = env_config['DOWNLOAD_URL_TYPE'] if env_config.get('DOWNLOAD_URL_TYPE') else compose_env_config['DOWNLOAD_URL_TYPE']

        Restore(
            db_path=db_path,
            network=service,
            download_path=restore_path,
            download_force=download_force,
            download_url=download_url,
            download_tool=download_tool,
            download_url_type=download_url_type,
        )

    def run(self, ):
        dump(self.config)
        self.config['settings']['env']['BASE_DIR'] = os.getcwd()
        self.config['settings']['env']['CONFIG_LOCAL_FILE'] = f'configure.yml'
        self.config['settings']['icon2']['GOLOOP_KEY_SECRET'] = f'keysecret'
        self.config['settings']['icon2']['GOLOOP_KEY_STORE'] = f'keystore.json'
        self.config['settings']['genesis_json'] = f'genesis.json'
        self.config['settings']['genesis_storage'] = f'gs.zip'
        self.config['settings']['iiss_json'] = f'icon_config.json'
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
