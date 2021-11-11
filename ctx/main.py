#!/usr/bin/with-contenv python3
# -*- coding: utf-8 -*-
import time
import asyncio

from config.configure import Configure as CFG

from manager.chain_init import ChainInit
from manager.node_checker import NodeChecker
from manager.ntp import NTPDaemon

cfg = CFG(use_file=True)
cfg.get_config(True)
for log_file in cfg.config['settings']['env']['COMPOSE_ENV'].get('DOCKER_LOG_FILES').split(','):
    cfg.loggers[log_file] = cfg.init_logger(log_file, 'debug')

# time.sleep(int(cfg.config['settings']['env'].get('MAIN_TIME_OUT', 15)))
cfg.logger = cfg.get_logger('chain.log')
cfg.logger.info("Start ChainInit()")

CI = ChainInit()
CI.starter()

cfg.logger = cfg.get_logger('health.log')
cfg.logger.info("Start NodeChecker()")
nc = NodeChecker()
cfg.logger.info("Start NTPDaemon()")
nd = NTPDaemon()

async def run_managers():
    await asyncio.wait([
        nc.check_node(),
        nd.sync_time()
    ])

asyncio.run(run_managers())
