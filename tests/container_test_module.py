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
    is_debug = True
    is_control_container = False
    container_path = "goloop_container"

    # @unittest.skip("test case skipping")
    def test_210_goloop_chain_leave(self):
        # res = self.exec_container("env && echo $GOLOOP_DATA_ROOT")
        self.is_debug = True
        res = self.exec_container("cp /ctx/mainnet_v1_block_proof/block_v1_proof.bin ${GOLOOP_DATA_ROOT}/1/")
        res = self.exec_container("ls ${GOLOOP_DATA_ROOT}/1/")

        # print(f"{res}")


if __name__ == "__main__":
    TestRunner().run()

