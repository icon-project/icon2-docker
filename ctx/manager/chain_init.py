#!/usr/bin/with-contenv python3
# -*- coding: utf-8 -*-
import os
import yaml
import time
import requests
import socket_request

from config.configure import Configure as CFG
from common.converter import str2bool
from common.icon2 import get_preps, get_inspect
from common.output import write_yaml, write_json

class ChainInit:
    def __init__(self, use_file=True):
        self.cfg = CFG(use_file=use_file)
        self.cfg.logger = self.cfg.get_logger('chain.log')
        self.config = self.cfg.config
        self.ctl = socket_request.ControlChain(
            unix_socket=self.cfg.config.get("CLI_SOCK", "/goloop/data/cli.sock"),
            debug=self.config['settings']['env'].get('CC_DEBUG', False)
        )
        self.base_dir = self.config['settings']['env'].get('BASE_DIR')

    def get_seeds(self, ):
        seeds = list()
        res = get_preps(self.config['settings']['env'].get('ENDPOINT'))
        if res.get('error'):
            self.cfg.logger.error(f"{res.get('error')}")
        else:
            preps_addr = [prep['nodeAddress']for prep in res['result']['preps']]
            inspect = get_inspect(
                self.config['settings']['env'].get('ENDPOINT'),
                self.config['settings']['env']['CID']
            )
            if inspect.get('error'):
                self.cfg.logger.error(f"[Control Chain] get inspect error - {inspect.get('error')}")
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

    def set_configure(self, wait_state=True):
        payload = {}
        prev_config = self.ctl.view_chain(detail=True).get_json()

        now_config = {
            "role": int(self.config['settings']['env'].get('ROLE', 0)),
            "seedAddress": self.config['settings']['env'].get('SEEDS', None),
            # "rpcIncludeDebug": self.config['settings']['env'].get('RPC_INCLUDE_DEBUG', False)
        }
        self.cfg.logger.info(f"Control Chain: prev_config={prev_config}")
        self.cfg.logger.info(f"Control Chain: now_config={now_config}")

        for config_key, config_value in now_config.items():
            if config_value is not None and prev_config.get(config_key, 'THIS_IS_ERROR_VALUE') != config_value:
                self.cfg.logger.info(f"Control Chain: Set configure key=\"{config_key}\", value=\"{prev_config.get(config_key)}\" => \"{config_value}\"")
                payload[config_key] = config_value

        if payload:
            self.ctl.stop()
            if wait_state:
                self.cfg.logger.info(f"***** Control Chain: wait_state={wait_state}")
                try:
                    res = self.ctl.chain_config(payload=payload)
                except Exception as e:
                    self.cfg.logger.error(f"[Control Chain] error chain_config - {e}")
            else:
                self.cfg.logger.info(f"***** Control Chain: stop()")
                self.ctl.stop()
                self.cfg.logger.info(f"***** Control Chain: Create ControlChain()")
                wait_ctl = socket_request.ControlChain(
                    unix_socket=self.cfg.config.get("CLI_SOCK", "/goloop/data/cli.sock"),
                    debug=self.config['settings']['env'].get('CC_DEBUG', False),
                    wait_state=wait_state
                )
                self.cfg.logger.info(f"***** Control Chain: chain_config()")
                res = wait_ctl.chain_config(payload=payload)

            if res and res.get_json()['state'] == "OK":
                self.cfg.logger.info(f"Control Chain: chain_config() => {res.get_json()['state']}")
            else:
                self.cfg.logger.error(f"Control Chain: got errors={res}")

            changed_res = self.ctl.view_chain(detail=True).get_json()
            for config_key, config_value in payload.items():
                if changed_res.get(config_key) == config_value:
                    self.cfg.logger.info(f"Control Chain: Successful Change key=\"{config_key}\", value=\"{changed_res[config_key]}\"")
                else:
                    self.cfg.logger.error(f"Control Chain: Failed Change key=\"{config_key}\", value=\"{config_value}\" => \"{changed_res[config_key]}\"")
        else:
            self.cfg.logger.info(f"Control Chain: Set configure, No actions")

    def starter(self, ):
        time.sleep(self.config['settings']['mig'].get('MIG_REST_TIME', 5))
        self.cfg.logger.info("-"*100)
        if not self.config['settings']['env'].get('SEEDS'):
            self.get_seeds()
        self.cfg.logger.info(f"Chain Starter: SEEDS={self.config['settings']['env'].get('SEEDS')}")
        if self.config['settings']['env'].get('FASTEST_START') is True:
            self.cfg.logger.info(f"Control Chain: START {self.ctl.get_state()}, FASTEST_START={self.config['settings']['env']['FASTEST_START']}")
            if self.config['settings']['mig'].get('MIG_COMPLETED') is False and self.config['settings']['mig'].get('MIGRATION_START') is True:
                self.cfg.logger.info(f"Migration DB Stage2")
                self.cfg.logger.info(f"Control Chain: START {self.ctl.get_state()}")
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
                self.cfg.logger.info(f"ICON2 DB after Stage3")
                self.ctl.start()
        else:
            res = self.ctl.get_state()
            if isinstance(res, dict) and res.get('cid', None) is None:
                res = self.ctl.join(
                    seedAddress=self.config['settings']['env'].get('SEEDS', '').split(','),
                    role=self.config['settings']['env'].get('ROLE', 0),
                    gs_file=self.config['settings'].get('genesis_storage', '/goloop/config/icon_genesis.zip')
                )
                self.cfg.logger.info(f"Please check joining: {res}")
                time.sleep(3)
            else:
                self.set_configure(wait_state=True)

            self.cfg.logger.info(f"Control Chain: START {self.ctl.get_state()}")
            self.ctl.start()
        rs = self.ctl.get_state()
        if rs.get('state') == 'started':
            self.cfg.logger.info(f"Control Chain: STATE [{rs.get('state')}]")
        else:
            self.cfg.logger.info(f"Control Chain: STATE [{rs.get('state')}]")


if __name__ == '__main__':
    CI = ChainInit()
