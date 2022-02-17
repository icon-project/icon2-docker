# -*- coding: utf-8 -*-

import os
import sys
import time
import asyncio

import unittest
from urllib.request import urlopen
import requests
from termcolor import cprint

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# parent_dir = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
# sys.path.append(parent_dir)
# sys.path.append(parent_dir + "/..")

# from ctx.common import base
# base.disable_ssl_warnings()


# from urllib3.exceptions import InsecureRequestWarning
# requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# import ssl
# ctx = ssl.create_default_context()
# ctx.check_hostname = False
# ctx.verify_mode = ssl.CERT_NONE


from set_tester import (
    set_os_env, set_docker_compose, remove_goloop_settings,
    goloop_chain_join, goloop_chain_leave, goloop_chain_ls,
    ContainerTestCase
)


FILE_PATH = os.path.dirname(os.path.realpath(__file__))


def is_responsive(url):
    try:
        try:
            response = requests.get(url)
            print(f"r={response}")
            if response.status_code == 200:
                return True
        except:
            return False
    except ConnectionError:
        return False


class TestNodeChecker(ContainerTestCase):
    # docker_compose_file = "sdsd"

    def __init__(self, value):
        super().__init__()

    def test_check_env(self, ):
        self.log_point(f"Web Config Test, {FILE_PATH}")
        _base_env = set_os_env(FILE_PATH)
        _service_url = f"{_base_env['CONFIG_URL']}/{_base_env['SERVICE']}"
        _config_url = f"{_service_url}/{_base_env['CONFIG_URL_FILE']}"

        # status_code = urlopen(_config_url).getcode()
        # cprint(f"=================={_config_url}")
        status_code = requests.get(_config_url).status_code
        self.assertTrue(status_code == 200, msg=f"Check url(={_config_url}).")
        self.log_point(" - Completed", "yellow")

    def run_container(self, ):

        self.copy_docker_compose(
            content={
                "services": {
                    "icon2-node": {
                        "environment": {
                            "SERVICE": "SejongNet"
                        }
                    }
                }
            }
        )

        # sys.exit()
        docker_compose = set_docker_compose(FILE_PATH)
        print(docker_compose)
        # _docker_start = f"cd {FILE_PATH}/goloop; docker-compose up -d"

        # self.execute("docker-compose ps")
        self.start_container()

        self.wait_until_responsive(
            timeout=2,
            pause=1,
            check=lambda: is_responsive("http://localhost:9000")
        )
        #
        # self.exec_container("icon2-node", "goloop version", expected_output="v1.2.1")

        # self.exec_container("icon2-node", "ls", "-al")


        #
        # self.stop_container()

        # self.assertRaises(Exception, self.execute(_docker_start))
        # self.assertRaises(Exception, os.system(_docker_start))
        # time.sleep(3)
        # self.assertRaises(Exception, os.system(goloop_chain_join()))
        # time.sleep(3)
        # self.assertRaises(Exception, os.system(goloop_chain_ls()))

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

    # def run(self, ):
    #     try:
    #         self.test_check_env()
    #         self.run_container()
    #     # self.test_node_checker()
    #     except KeyboardInterrupt:
    #         self.log_point("KeyboardInterrupt, It will be terminated container", "red")
    #         self.stop_container()
    #         self.log_point("Terminated container", "red")


if __name__ == "__main__":
    # TNC = TestNodeChecker()
    # TNC.run()
    unittest.main()
