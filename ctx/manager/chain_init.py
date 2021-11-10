#!/usr/bin/with-contenv python3
# -*- coding: utf-8 -*-
import os
import sys
import yaml
import time
import requests
import socket_request

from config.configure import Configure as CFG
from common.converter import str2bool
from common.icon2 import get_preps, get_inspect
from common.output import write_yaml, write_json, open_json


class ChainInit:
    def __init__(self, use_file=True):
        self.cfg = CFG(use_file=use_file)
        self.cfg.logger = self.cfg.get_logger('chain.log')
        self.config = self.cfg.config
        self.unix_socket = self.config['settings']['icon2'].get("GOLOOP_NODE_SOCK", "/goloop/data/cli.sock")
        self.ctl = socket_request.ControlChain(
            unix_socket=self.unix_socket,
            debug=self.config['settings']['env'].get('CC_DEBUG', False),
            timeout=int(self.config['settings']['env'].get('MAIN_TIME_OUT', 30)),
            logger=self.cfg.logger,
            retry=3
        )
        self.chain_socket_checker()
        self.base_dir = self.config['settings']['env'].get('BASE_DIR')

    def chain_socket_checker(self, ):
        try_cnt = 0
        while self.ctl.health_check().status_code != 200:
            main_retry_count = int(self.config['settings']['env'].get('MAIN_RETRY_COUNT', 200))
            sleep_count = int(self.config['settings']['env'].get('MAIN_TIME_SLEEP', 1))
            self.cfg.logger.info(f"[CC][{try_cnt}/{main_retry_count}] {self.ctl.health_check()}, try sleep {sleep_count}s")
            if try_cnt >= main_retry_count:
                self.cfg.logger.error(f"[CC] Socket connection failed. {self.unix_socket}")
                sys.exit(127)
            try_cnt += 1
            time.sleep(sleep_count)

    def get_seeds(self, ):
        seeds = list()
        res = get_preps(self.config['settings']['env'].get('ENDPOINT'))
        if res.get('error'):
            self.cfg.logger.error(f"get_preps() {res.get('error')}")
        else:
            preps_addr = [prep['nodeAddress']for prep in res['result']['preps']]
            inspect = get_inspect(
                self.config['settings']['env'].get('ENDPOINT'),
                self.config['settings']['env']['CID']
            )
            if inspect.get('error'):
                self.cfg.logger.error(f"[CC] get inspect error - {inspect.get('error')}")
            else:
                for p2p_addr, prep_addr in inspect['module']['network']['p2p']['roots'].items():
                    if prep_addr in preps_addr:
                        seeds.append(p2p_addr)
                self.cfg.logger.info(f"PREPs_count={len(res['result']['preps'])}")
                self.config['settings']['env']['SEEDS'] = ",".join(seeds)
                self.cfg.logger.info(f"SEEDS={self.config['settings']['env']['SEEDS']}")
                file_name = self.config['settings']['env'].get('CONFIG_LOCAL_FILE', '/goloop/configure.yml')
                rs = write_yaml(
                    file_name,
                    self.config
                )
                self.cfg.logger.info(f"{rs}")

    def get_my_info(self):
        res = get_preps(self.config['settings']['env'].get('ENDPOINT'))
        prep_info = {}
        if res.get('error'):
            self.cfg.logger.error(f"get_preps() {res.get('error')}")
        else:
            try:
                keystore_file = open_json(self.config['settings']['icon2']['GOLOOP_KEY_STORE'])
                my_address = keystore_file.get("address")
            except Exception as e:
                self.cfg.logger.error(f"[ERROR] Load keystore - {e}")
                my_address = None

            if my_address:
                for prep in res['result']['preps']:
                    if prep['nodeAddress'] == my_address:
                        prep_info = prep

            if prep_info:
                self.cfg.logger.info(f"[CC] P-Rep Info name: {prep_info.get('name')}, grade: {prep_info.get('grade')}")
            else:
                self.cfg.logger.error(f"[CC] It's not a registered keystore(wallet). "
                                      f"check your keystore -> {my_address}")
        return {}

    def set_configure(self, wait_state=True):
        payload = {}
        prev_config = self.ctl.view_chain(detail=True).get_json()

        now_config = {
            "role": int(self.config['settings']['env'].get('ROLE', 0)),
            "seedAddress": self.config['settings']['env'].get('SEEDS', None),
            # "rpcIncludeDebug": self.config['settings']['env'].get('RPC_INCLUDE_DEBUG', False)
        }
        self.cfg.logger.info(f"[CC] prev_config={prev_config}")
        self.cfg.logger.info(f"[CC] now_config={now_config}")

        for config_key, config_value in now_config.items():
            if config_value is not None and prev_config.get(config_key, 'THIS_IS_ERROR_VALUE') != config_value:
                self.cfg.logger.info(f"CC: Set configure key=\"{config_key}\", value=\"{prev_config.get(config_key)}\" => \"{config_value}\"")
                payload[config_key] = config_value

        if payload:
            self.ctl.stop()
            if wait_state:
                self.cfg.logger.info(f"[CC] wait_state={wait_state}")
                try:
                    res = self.ctl.chain_config(payload=payload)
                except Exception as e:
                    res = None
                    self.cfg.logger.error(f"[CC] error chain_config - {e}")
            else:
                self.cfg.logger.info(f"[CC] stop()")
                self.ctl.stop()
                self.cfg.logger.info(f"[CC] Create ControlChain()")
                wait_ctl = socket_request.ControlChain(
                    unix_socket=self.unix_socket,
                    debug=self.config['settings']['env'].get('CC_DEBUG', False),
                    wait_state=wait_state
                )
                self.cfg.logger.info(f"[CC] chain_config()")
                res = wait_ctl.chain_config(payload=payload)

            if res and res.get_json()['state'] == "OK":
                self.cfg.logger.info(f"[CC] chain_config() => {res.get_json()['state']}")
            else:
                self.cfg.logger.error(f"[CC] got errors={res}")

            changed_res = self.ctl.view_chain(detail=True).get_json()
            for config_key, config_value in payload.items():
                if changed_res.get(config_key) == config_value:
                    self.cfg.logger.info(f"[CC] Successful Change key=\"{config_key}\", value=\"{changed_res[config_key]}\"")
                else:
                    self.cfg.logger.error(f"[CC] Failed Change key=\"{config_key}\", value=\"{config_value}\" => \"{changed_res[config_key]}\"")
        else:
            self.cfg.logger.info(f"[CC] Set configure, No actions")

    def starter(self, ):
        time.sleep(self.config['settings']['mig'].get('MIG_REST_TIME', 5))

        if int(self.config['settings']['env'].get('ROLE')) == 3:
            self.get_my_info()

        self.cfg.logger.info("-"*100)
        if not self.config['settings']['env'].get('SEEDS'):
            self.get_seeds()
        self.cfg.logger.info(f"[CC] Starter: SEEDS={self.config['settings']['env'].get('SEEDS')}")
        if self.config['settings']['env'].get('FASTEST_START') is True:
            self.cfg.logger.info(f"[CC] START {self.ctl.get_state()}, FASTEST_START={self.config['settings']['env']['FASTEST_START']}")
            if self.config['settings']['mig'].get('MIG_COMPLETED') is False and self.config['settings']['mig'].get('MIGRATION_START') is True:
                self.cfg.logger.info(f"[CC] Migration DB Stage2")
                self.cfg.logger.info(f"[CC] START {self.ctl.get_state()}")
                payload = {
                    "store_uri": f"{self.config['settings']['mig'].get('MIG_ENDPOINT')}/api/v3",
                    "config_url": self.config['settings']['mig'].get('MIG_CONFIG_URL'),
                    "max_rps": int(self.config['settings']['mig'].get('MIG_RPS'))
                }
                write_json(
                    f"{os.path.join(self.base_dir, 'import_config.json')}",
                    payload
                )
                self.set_configure(wait_state=False)
                self.ctl.import_icon(payload=payload)
            else:
                self.set_configure(wait_state=True)
                self.cfg.logger.info(f"[CC] ICON2 DB after Stage3")
                self.ctl.start()
        else:
            res = self.ctl.get_state()
            if isinstance(res, dict) and res.get('cid', None) is None:
                res = self.ctl.join(
                    seedAddress=self.config['settings']['env'].get('SEEDS', '').split(','),
                    role=self.config['settings']['env'].get('ROLE', 0),
                    gs_file=self.config['settings'].get('genesis_storage', '/goloop/config/icon_genesis.zip')
                )
                self.cfg.logger.info(f"[CC] Please check joining: {res}")
                time.sleep(3)
            else:
                self.set_configure(wait_state=True)

            self.cfg.logger.info(f"[CC] START {self.ctl.get_state()}")
            self.ctl.start()
        rs = self.ctl.get_state()
        if rs.get('state') == 'started':
            self.cfg.logger.info(f"[CC] STATE [{rs.get('state')}]")
        else:
            self.cfg.logger.info(f"[CC] STATE [{rs.get('state')}]")


if __name__ == '__main__':
    CI = ChainInit()
