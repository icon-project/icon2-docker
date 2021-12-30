#!/usr/bin/with-contenv python3
# -*- coding: utf-8 -*-
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.configure import Configure as CFG
from config.configure_setter import ConfigureSetter as CS
from common import resources


class InitManager:
    def __init__(self, ):
        self.cfg = CFG() # Configure
        if self.cfg.base_env['ONLY_GOLOOP'] is False:
            self.cs = CS()# ConfigureSetter

    def run(self, ):
        self.print_banner()
        self.print_resources()
        self.cfg.logger.info(f"[INIT_CONFIG] Initializing Configuration")
        for key, value in self.cfg.base_env.items():
            self.cfg.logger.info(f"[INIT_CONFIG] {key} = {value} ({type(value).__name__})")

        if self.cfg.base_env.get('LOCAL_TEST') is True:
            ip_type = "LOCAL_TEST"
        else:
            ip_type = "PUBLIC"
        self.cfg.logger.info(f"[INIT_CONFIG] GOLOOP_P2P = \"{self.cfg.config['GOLOOP_P2P']}\" ({ip_type})")

        if self.cfg.config:
            for key, value in self.cfg.config.items():
                if key == 'KEY_PASSWORD' and len(value):
                    value = '*' * len(str(value))
                if key.startswith("GOLOOP") is False:
                    self.cfg.logger.info(f"[CTX] {key} = {value} ({type(value).__name__})")

        if self.cfg.config:
            for key, value in self.cfg.config.items():
                if key.startswith("GOLOOP") is True and value is not None:
                    self.cfg.logger.info(f"[ICON2] {key} = {value} ({type(value).__name__})")

        self.cs.create_yaml_file()
        self.cs.create_env_file()
        self.cs.make_base_dir()
        self.cs.create_key()
        self.cs.create_genesis_json()
        self.cs.create_gs_zip()
        self.cs.create_icon_config()
        self.cs.create_db()
        self.cfg.logger.info("--- Finish initializing ---")

    def print_banner(self):
        v_info = self.cfg.get_version()
        config_version = self.cfg.config.get('version')
        self.cfg.logger.info(f" ██████╗████████╗██╗  ██╗")
        self.cfg.logger.info(f"██╔════╝╚══██╔══╝╚██╗██╔╝ Goloop Version:  {v_info.get('VERSION')}")
        self.cfg.logger.info(f"██║        ██║    ╚███╔╝  CTX Version:     {v_info.get('VCS_REF')}")
        self.cfg.logger.info(f"██║        ██║    ██╔██╗  Config Version:  {config_version}")
        self.cfg.logger.info(f"╚██████╗   ██║   ██╔╝ ██╗ Build Date:      {v_info.get('BUILD_DATE')}")
        self.cfg.logger.info(f" ╚═════╝   ╚═╝   ╚═╝  ╚═╝ ")

    def print_resources(self):
        try:
            self.cfg.logger.info(f"[RESOURCES] System Information: {resources.get_platform_info()}")
            self.cfg.logger.info(f"[RESOURCES] Memory Information: {resources.get_mem_info(unit='GB')}")
            self.cfg.logger.info(f"[RESOURCES] rlimit Information: {resources.get_rlimit_nofile()}")
        except Exception as e:
            self.cfg.logger.error(f"get resource error - {e}")


if __name__ == '__main__':
    IM = InitManager()
    if IM.cfg.base_env['ONLY_GOLOOP'] is False:
        IM.run()
