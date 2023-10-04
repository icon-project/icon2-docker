#!/usr/bin/with-contenv python3
# -*- coding: utf-8 -*-
import time
import asyncio

from config.configure import Configure as CFG

from manager.chain_init import ChainInit
from manager.node_checker import NodeChecker
from manager.ntp import NTPDaemon
from common.runner import AsyncRunner
from pawnlib.utils.operate_handler import run_with_keyboard_interrupt


async def run_managers(command_list=None):
    if isinstance(command_list, list):
        _command_list = []
        for command in command_list:
            _command_list.append(asyncio.create_task(command))
        command_list = _command_list
        await asyncio.wait(command_list)


def main():
    cfg = CFG(use_file=True)

    if cfg.base_env['ONLY_GOLOOP'] is True:
        cfg.logger.info('Using ONLY_GOLOOP')
        cfg.send_auto_slack(
            title='Starting Node [ONLY_GOLOOP]',
            msg_text=cfg.export_major_config(),
            msg_level='info'
        )
    else:
        cfg.get_config(True)
        for log_file in cfg.config.get('DOCKER_LOG_FILES').split(','):
            cfg.loggers[log_file] = cfg.init_logger(log_file, 'debug')

        cfg.logger = cfg.get_logger('chain.log')
        cfg.logger.info("Start ChainInit()")

        CI = ChainInit()
        CI.starter()

    async_runner = AsyncRunner()
    cfg.logger = cfg.get_logger('health.log')

    _use_health_check = cfg.get_base_config('USE_HEALTH_CHECK')
    _use_ntp_sync = cfg.get_base_config('USE_NTP_SYNC')

    if _use_health_check:
        cfg.logger.info("Start NodeChecker()")
        nc = NodeChecker()
        async_runner.push(nc.check_node())
    else:
        cfg.logger.info(f"Disabled NodeChecker(), USE_HEALTH_CHECK={_use_health_check}")

    if _use_ntp_sync:
        cfg.logger.info("Start NTPDaemon()")
        nd = NTPDaemon()
        async_runner.push(nd.sync_time())
    else:
        cfg.logger.info(f"Disabled NTPDaemon(), USE_NTP_SYNC={_use_ntp_sync}")

    if len(async_runner.command_list) > 0:
        cfg.logger.info(f"async_command_list = {async_runner.command_list}")
        async_runner.run()

    else:
        while True:
            time.sleep(60)


if __name__ == "__main__":
    run_with_keyboard_interrupt(main)
