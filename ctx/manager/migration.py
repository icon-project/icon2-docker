#!/usr/bin/with-contenv python3
# -*- coding: utf-8 -*-
import os
import json
import yaml
import time
import requests
import subprocess

from ..config.configure import Configure as CFG


class Migration:
    def __init__(self, use_file=True):
        self.cfg = CFG(use_file=use_file)
        self.config = self.cfg.config
        self.get_config()
        self.data_dir = "/goloop/data"
        if self.config['settings']['env'].get('BASE_DIR'):
            self.data_dir = f"{self.config['settings']['env'].get('BASE_DIR')}/data"
        self.config_dir = "/goloop/config"
        if self.config['settings']['env'].get('BASE_DIR'):
            self.config_dir = f"{self.config['settings']['env'].get('BASE_DIR')}/config"
        self.p2p_listen = os.getenv('GOLOOP_P2P_LISTEN', '7100').split(':')[-1]

    def get_config(self, ):
        res = requests.get(self.config['settings']['env'].get(
            'MIG_INFO_DATA_URL',
            self.config['settings']['env']['COMPOSE_ENV'].get('MIG_INFO_DATA_URL')
        ))
        if res.status_code == 200:
            self.config['settings']['mig'] = yaml.load(res.text, Loader=yaml.FullLoader)
        for mig_key in self.config['settings']['mig'].keys():
            if self.config['settings']['env'].get(mig_key):
                self.config['settings']['mig'][mig_key] = self.config['settings']['env'].get(mig_key)

    def icon2_join(self, db_type='rocksdb'):
        seeds = f'127.0.0.1:{self.p2p_listen}'
        _ = subprocess.check_output(f"goloop chain join --platform icon \
                --channel icon_dex \
                --genesis /goloop/config/icon_genesis.zip \
                --tx_timeout 60000 \
                --node_cache small \
                --normal_tx_pool 10000 \
                --db_type {db_type} \
                --seed {self.config['settings']['env'].get('SEEDS', seeds)}", shell=True).split('\n')[0]

    def icon2_import(self, rps=30, use_db=False):
        mig_endpoint = ''
        mig_config_url = ''
        if use_db:
            store_uri = f"{self.config['settings']['mig'].get('MIG_ENDPOINT', mig_endpoint)}/api/v3"
        else:
            store_uri = f"/goloop/icon/MainNet/.storage/db_icon_dex,{self.config['settings']['mig'].get('MIG_ENDPOINT', mig_endpoint)}/api/v3"
        import_config = {
            "store_uri": store_uri,
            "config_url": self.config['settings']['mig'].get('MIG_CONFIG_URL', mig_config_url),
            "max_rps": int(rps)
        }
        cmd_list = [
            f"echo '{json.dumps(import_config)}' > {os.path.join(self.config_dir, 'import_config.json')}",
            f"goloop chain import_icon {self.config['settings']['env'].get('CID', '0x1')} @{self.config['settings']['env'].get('BASE_DIR', '/goloop')}/config/import_config.json"
        ]
        for cmd in cmd_list:
            _ = self.run_cmd(cmd)

    def run_cmd(self, cmd):
        try:
            return subprocess.check_output(cmd, shell=True)
        except subprocess.CalledProcessError as e:
            return e
        except Exception as e:
            return e

    def run(self, ):
        time.sleep(self.config['settings']['mig'].get('MIG_REST_TIME', 5))
        if self.config['settings']['mig'].get('MIGRATION_START'):
            self.icon2_import(use_db=True)


if __name__ == '__main__':
    MIG = Migration()
    MIG.run()