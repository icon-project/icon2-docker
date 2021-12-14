#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import append_parent_path

from config.configure import Configure as CFG
from config.configure_setter import ConfigureSetter as CS
from devtools import debug

cfg = CFG()  # Configure
cs = CS()  # ConfigureSetter
debug(cfg)


# cs.create_yaml_file()
# cs.create_env_file()
#
# debug(cfg.config['GOLOOP_LOG_WRITER_FILENAME'])

