#!/usr/bin/with-contenv python3
# -*- coding: utf-8 -*-
import time
import asyncio

from config.configure import Configure as CFG

from manager.chain_init import ChainInit
from manager.node_checker import NodeChecker
from manager.ntp import NTPDaemon

cfg = CFG(use_file=True)
if cfg.base_env['ONLY_GOLOOP'] is True:
    while True:
        time.sleep(1000)
cfg.get_config(True)
for log_file in cfg.config.get('DOCKER_LOG_FILES').split(','):
    cfg.loggers[log_file] = cfg.init_logger(log_file, 'debug')

cfg.logger = cfg.get_logger('chain.log')
cfg.logger.info("Start ChainInit()")

CI = ChainInit()
CI.starter()

async_command_list = []
cfg.logger = cfg.get_logger('health.log')
if cfg.config.get('USE_HEALTH_CHECK'):
    cfg.logger.info("Start NodeChecker()")
    nc = NodeChecker()
    async_command_list.append(nc.check_node())
else:
    cfg.logger.info(f"Disabled NodeChecker(), USE_HEALTH_CHECK={cfg.config.get('USE_HEALTH_CHECK')}")

if cfg.config.get('USE_NTP_SYNC'):
    cfg.logger.info("Start NTPDaemon()")
    nd = NTPDaemon()
    async_command_list.append(nd.sync_time())
else:
    cfg.logger.info(f"Disabled NTPDaemon(), USE_NTP_SYNC={cfg.config.get('USE_NTP_SYNC')}")


async def run_managers(command_list=None):
    if isinstance(command_list, list):
        await asyncio.wait(command_list)

if len(async_command_list) > 0:
    asyncio.run(run_managers(async_command_list))
else:
    while True:
        time.sleep(60)
