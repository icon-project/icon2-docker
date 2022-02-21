# -*- coding: utf-8 -*-

import os
import sys
import time
import asyncio

import unittest
from urllib.request import urlopen
from termcolor import cprint

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from set_tester import (
    set_os_env, set_docker_compose, remove_goloop_settings,
    goloop_chain_join, goloop_chain_leave, goloop_chain_ls
)


FILE_PATH = os.path.dirname(os.path.realpath(__file__))


class TestNodeChecker(unittest.TestCase):

    def test_check_env(self, ):
        cprint("Web Config Test", "green")
        _base_env = set_os_env(FILE_PATH)
        _service_url = f"{_base_env['CONFIG_URL']}/{_base_env['SERVICE']}"
        _config_url = f"{_service_url}/{_base_env['CONFIG_URL_FILE']}"
        status_code = urlopen(_config_url).getcode()
        self.assertTrue(status_code == 200, msg=f"Check url(={_config_url}).")
        cprint(" - Completed", "yellow")

    def run_container(self, ):
        set_docker_compose(FILE_PATH)
        _docker_start = f"cd {FILE_PATH}/goloop; docker-compose up -d"
        self.assertRaises(Exception, os.system(_docker_start))
        time.sleep(3)
        self.assertRaises(Exception, os.system(goloop_chain_join()))
        time.sleep(3)
        self.assertRaises(Exception, os.system(goloop_chain_ls()))

    def test_node_checker(self, ):
        cprint("Node Checker Test", "green")
        time.sleep(5)
        _docker_stop = f"cd {FILE_PATH}/goloop; docker-compose down"
        _base_env = set_os_env(FILE_PATH)
        self.assertRaises(Exception, asyncio.run(self.run_managers()))
        self.assertRaises(Exception, os.system(goloop_chain_leave()))
        self.assertRaises(Exception, os.system(_docker_stop))
        remove_goloop_settings(FILE_PATH)
        cprint(" - Completed", "yellow")

    async def run_managers(self, ):
        from config.configure import Configure as CFG
        from manager.node_checker import NodeChecker
        _cfg = CFG(use_file=False)
        _cfg.config['IS_TEST'] = True
        _nc = NodeChecker()
        await asyncio.wait([
            _nc.check_node()
        ])

    def run(self, ):
        self.test_check_env()
        self.run_container()
        self.test_node_checker()


if __name__ == "__main__":
    TNC = TestNodeChecker()
    TNC.run()