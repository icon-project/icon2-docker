#!/usr/bin/with-contenv python3
# -*- coding: utf-8 -*-
import os
import sys
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.configure import Configure as CFG
from config.configure_setter import ConfigureSetter as CS


class InitManager:
    def __init__(self, ):
        self.cfg = CFG() # Configure
        self.cs = CS() # ConfigureSetter

    def run(self, ):
        self.cfg.logger.info(f"[INIT_CONFIG] Initializing Configuration")
        for key, value in self.cfg.compose_env.items():
            self.cfg.logger.info(f"[INIT_CONFIG] {key} = {value} ({type(value).__name__})")

        if self.cfg.compose_env.get('LOCAL_TEST'):
            ip_type = "LOCAL_TEST"
        else:
            ip_type = "PUBLIC"
        self.cfg.logger.info(f"[INIT_CONFIG] GOLOOP_P2P = \"{self.cfg.config['settings']['icon2']['GOLOOP_P2P']}\" ({ip_type})")

        settings = self.cfg.config['settings']['env']
        if settings:
            for key, value in settings.items():
                if key != "COMPOSE_ENV":
                    self.cfg.logger.info(f"[DOCKER_ENV] {key} = {value} ({type(value).__name__})")

        self.cs.create_yaml_file()
        self.cs.create_env_file()
        self.cs.make_base_dir()
        if self.cfg.config['settings']['env'].get('IS_AUTOGEN_CERT'):
            self.cs.create_key()
        self.cs.create_genesis_json()
        self.cs.create_gs_zip()
        self.cs.create_icon_config()
        self.cs.create_db()
        self.cfg.logger.info("--- Finish initializing ---")


if __name__ == '__main__':
    IM = InitManager()
    IM.run()
