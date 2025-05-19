#!/usr/bin/with-contenv python3
# -*- coding: utf-8 -*-
import os
import sys
import time
import socket_request
from shutil import copy2

from config.configure import Configure as CFG
from common.icon2 import get_preps, get_inspect
from common.output import write_yaml, open_json


class ChainInit:
    def __init__(self, use_file=True):
        self.cfg = CFG(use_file=use_file)
        self.cfg.logger = self.cfg.get_logger('chain.log')
        self.config = self.cfg.config
        self.unix_socket = self.config.get("GOLOOP_NODE_SOCK", "/goloop/data/cli.sock")
        self.ctl = socket_request.ControlChain(
            unix_socket=self.unix_socket,
            debug=self.config.get('CC_DEBUG', False),
            timeout=int(self.config.get('MAIN_TIME_OUT', 30)),
            logger=self.cfg.logger,
            retry=3
        )
        self.chain_socket_checker()
        self.base_dir = self.config.get('BASE_DIR')

    def chain_socket_checker(self, ):
        try_cnt = 0
        while self.ctl.health_check().status_code != 200:
            main_retry_count = int(self.config.get('MAIN_RETRY_COUNT', 200))
            sleep_count = int(self.config.get('MAIN_TIME_SLEEP', 1))
            self.cfg.logger.info(f"[CC][{try_cnt}/{main_retry_count}] {self.ctl.health_check()}, try sleep {sleep_count}s")
            if try_cnt >= main_retry_count:
                self.cfg.logger.error(f"[CC] Socket connection failed. {self.unix_socket}")
                sys.exit(127)
            try_cnt += 1
            time.sleep(sleep_count)

    def get_seeds(self, ):
        seeds = list()
        res = get_preps(self.config.get('ENDPOINT'))
        if res.get('error'):
            self.cfg.logger.error(f"get_preps() {res.get('error')}")
        else:
            preps_addr = [prep['nodeAddress'] for prep in res['result']['preps']]
            inspect = get_inspect(
                self.config.get('ENDPOINT'),
                self.config['CID']
            )
            if inspect.get('error'):
                self.cfg.logger.error(f"[CC] get inspect error - {inspect.get('error')}")
            else:
                for p2p_addr, prep_addr in inspect['module']['network']['p2p']['roots'].items():
                    if prep_addr in preps_addr:
                        seeds.append(p2p_addr)
                self.cfg.logger.info(f"PREPs_count={len(res['result']['preps'])}")
                self.config['SEEDS'] = ",".join(seeds)
                self.cfg.logger.info(f"SEEDS={self.config['SEEDS']}")
                file_name = self.config.get('CONFIG_LOCAL_FILE', '/goloop/configure.yml')
                rs = write_yaml(
                    file_name,
                    self.config
                )
                self.cfg.logger.info(f"{rs}")

    def get_my_info(self):
        res = get_preps(self.config.get('ENDPOINT'))
        prep_info = {}
        if res.get('error'):
            self.cfg.logger.error(f"get_preps() {res.get('error')}")
        else:
            try:
                keystore_file = open_json(self.config['GOLOOP_KEY_STORE'])
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
            "role": int(self.config.get('ROLE', 0)),
            "seedAddress": self.config.get('SEEDS', None)
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
                    debug=self.config.get('CC_DEBUG', False),
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

    def set_system_config(self):
        try:
            # system_config = ["rpcIncludeDebug", "rpcBatchLimit", "rpcDefaultChannel", "eeInstances"]
            system_config = self.ctl.view_system_config().get("config")
            new_system_config = {}
            for system_key, value in system_config.items():
                env_value = os.getenv(system_key, "__NOT_DEFINED__")
                if env_value != '__NOT_DEFINED__':
                    if str(value).lower() != env_value:
                        new_system_config[system_key] = env_value
                        self.cfg.logger.info(f"[CC] Set environment '{system_key}' => '{env_value}'")
                    else:
                        self.cfg.logger.info(f"[CC] Already set environment '{system_key}' => '{env_value}'")
            if new_system_config:
                self.cfg.logger.info(f"[CC][before] system_config = {system_config}")
                res = self.ctl.system_config(payload=new_system_config)
                self.cfg.logger.info(f"[CC][after] system_config = {res}")

        except Exception as e:
            self.cfg.logger.error(f"[CC] Set system config :: {e}")

    def starter(self, ):
        # time.sleep(self.config['settings']['mig'].get('MIG_REST_TIME', 5))
        if int(self.config.get('ROLE')) == 3:
            self.get_my_info()

        if self.config.get('FASTEST_START') is True:
            self.cfg.logger.info(f"[CC] START {self.ctl.get_state()}, FASTEST_START={self.config['FASTEST_START']}")
            self.set_configure(wait_state=True)
            self.cfg.logger.info(f"[CC] ICON2 DB after migration")
            self.ctl.start()
        else:
            if not self.config.get('SEEDS'):
                self.cfg.logger.error(f"Please check the SEEDS (Now={self.config.get('SEEDS')})")
                sys.exit(127)
            self.cfg.logger.info(f"[CC] Starter: SEEDS={self.config.get('SEEDS')}")
            res = self.ctl.get_state()
            if isinstance(res, dict) and res.get('cid', None) is None:
                network_name = self.config.get('SERVICE')
                self.cfg.logger.info(f"[CC] Join the Network, {network_name}")

                if network_name == "MainNet":
                    self.ctl.wait_state = False

                res = self.ctl.join(
                    seedAddress=self.config.get('SEEDS', '').split(','),
                    role=self.config.get('ROLE', 0),
                    gs_file=self.config.get('GENESIS_STORAGE', '/goloop/config/icon_genesis.zip'),
                )
                self.cfg.logger.info(f"[CC] Please check joining: {res}")
                time.sleep(3)

                if network_name == "MainNet":
                    v1_proof_file = "/ctx/mainnet_v1_block_proof/block_v1_proof.bin"
                    mainnet_data_dir = f"{self.config.get('GOLOOP_NODE_DIR')}/1"
                    self.cfg.logger.info(f"[CC] Copy {v1_proof_file} to {mainnet_data_dir}")
                    try:
                        copy2(v1_proof_file, f"{mainnet_data_dir}/")
                    except Exception as e:
                        self.cfg.logger.info(f"[CC] Copy error - {e}")
                    self.ctl.wait_state = True
                    self.ctl.start()
            else:
                self.set_configure(wait_state=True)

            self.cfg.logger.info(f"[CC] START {self.ctl.get_state()}")
            self.ctl.start()
        rs = self.ctl.get_state()

        self.set_system_config()

        if rs.get('state') == 'started':
            self.cfg.logger.info(f"[CC] STATE [{rs.get('state')}]")
        else:
            self.cfg.logger.info(f"[CC] STATE [{rs.get('state')}]")


if __name__ == '__main__':
    CI = ChainInit()
