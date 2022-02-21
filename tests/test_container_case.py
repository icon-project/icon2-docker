# -*- coding: utf-8 -*-
import append_parent_path
import os
import asyncio
import unittest
import requests

from container_tester import (
    set_os_env, ContainerTestCase, TestRunner
)

FILE_PATH = os.path.dirname(os.path.realpath(__file__))


class TestNodeChecker(ContainerTestCase):
    docker_compose_content = {
        "services": {
            "icon2-node": {
                "environment": {
                    "IS_AUTOGEN_CERT": "true",
                    # "SERVICE": "SejongNet",
                    "FASTEST_START": "false",
                    "KEY_STORE_FILENAME": "keystore.json",
                    "ROLE": 3,
                    # "LOG_OUTPUT_TYPE": "debug",
                },
                "network_mode": "bridge",
                "ports": ["9000:9000"]
            }
        }
    }
    # is_debug = True
    container_path = "goloop_container"

    def test_000_download_environment_file(self, ):

        _base_env = set_os_env(FILE_PATH)
        _service = _base_env['SERVICE']
        if self.get_service():
            _service = self.get_service()
        _service_url = f"{_base_env['CONFIG_URL']}/{_service}"
        _config_url = f"{_service_url}/{_base_env['CONFIG_URL_FILE']}"

        self.log_point(f"Web Config Test, {_config_url}", color="white")
        # status_code = urlopen(_config_url).getcode()
        # cprint(f"=================={_config_url}")
        status_code = requests.get(_config_url).status_code
        self.assertTrue(status_code == 200, msg=f"Check url(={_config_url}).")

    # @unittest.skip("test case skipping")
    def test_100_increase_blockheight(self):
        self.wait_until_blockheight(
            timeout=60,
            pause=1,
            reach_block=5,
        )

    # @unittest.skip("test case skipping")
    def test_210_goloop_chain_leave(self):
        self.exec_container("goloop chain leave icon_dex")

    # @unittest.skip("test case skipping")
    def test_220_goloop_chain_join(self):
        self.control_chain_join()

    # @unittest.skip("test case skipping")
    def test_240_control_chain_stop(self):
        self.exec_container("control_chain stop")

    # @unittest.skip("test case skipping")
    def test_250_goloop_chain_start(self):
        self.exec_container("goloop chain start icon_dex")

    # @unittest.skip("test case skipping")
    def test_260_increase_blockheight(self):
        self.wait_until_blockheight(
            timeout=60,
            pause=1,
            reach_block=5
        )

    def test_goloop_version(self):
        version = self.get_goloop_version()
        self.log_point(f"version = {version}, service={self.get_service()}", "white")
        self.exec_container("goloop version", expected_output=version)

    @unittest.skip("test case skipping")
    def test_get_service(self):
        version = self.execute("make version").strip()
        self.log_point(f"version = {version}", "white")
        self.exec_container("goloop version", expected_output=version)

    async def run_managers(self, ):
        from ctx.config.configure import Configure as CFG
        from ctx.manager.node_checker import NodeChecker
        _cfg = CFG(use_file=False)
        _cfg.config['IS_TEST'] = True
        _nc = NodeChecker()
        await asyncio.wait([
            _nc.check_node()
        ])

    @unittest.skip("Required checking")
    def test_run_managers(self):
        asyncio.run(self.run_managers())


if __name__ == "__main__":
    TestRunner().run()

