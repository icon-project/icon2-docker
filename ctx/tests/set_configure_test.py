#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import append_parent_path

from config.configure import Configure as CFG
from config.configure_setter import ConfigureSetter as CS
from manager.chain_init import ChainInit

from devtools import debug

cfg = CFG(use_file=False)  # Configure
cs = CS()  # ConfigureSetter

# cfg.get_config(use_file=False)

debug(cfg.config)
debug(cfg.base_env)
# debug(cfg.config)


# CI = ChainInit()
# CI.starter()
# CI.set_system_config()

exit()
if cfg.config:
    for key, value in cfg.config.items():
        if key == 'KEY_PASSWORD' and len(value):
            value = '*' * len(str(value))
        if key.startswith("GOLOOP") is False:
            cfg.logger.info(f"[CTX] {key} = {value} ({type(value).__name__})")
