# -*- coding: utf-8 -*-

import os
import sys
import yaml

from urllib.request import urlopen

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common import converter


def set_os_env(home_path:str):
    os.environ['CONFIG_URL'] = "https://networkinfo.solidwallet.io/node_info"
    os.environ['SERVICE'] = "MainNet"
    os.environ['CONFIG_URL_FILE'] = "default_configure.yml"
    os.environ['CONFIG_LOCAL_FILE'] = f"{home_path}/goloop/configure.yml"
    os.environ['LOCAL_TEST'] = "False"
    os.environ['BASE_DIR'] = f"{home_path}/goloop"
    os.environ['ONLY_GOLOOP'] = "False"
    os.environ['GOLOOP_P2P_LISTEN'] = ":7100"
    os.environ['GOLOOP_RPC_ADDR'] = ":9000"
    os.environ['DOCKER_LOG_FILES'] = "chain.log,health.log,error.log,debug.log"
    os.environ['CHECK_STACK_LIMIT'] = "1"
    temp_env = dict()
    temp_env['CONFIG_URL'] = os.getenv('CONFIG_URL', 'https://networkinfo.solidwallet.io/node_info')
    temp_env['SERVICE'] = os.getenv('SERVICE', 'MainNet')
    temp_env['CONFIG_URL_FILE'] = os.getenv('CONFIG_URL_FILE', 'default_configure.yml')
    temp_env['CONFIG_LOCAL_FILE'] = os.getenv('CONFIG_LOCAL_FILE', '/goloop/configure.yml')
    temp_env['LOCAL_TEST'] = converter.str2bool(os.getenv('LOCAL_TEST', False))
    temp_env['BASE_DIR'] = os.getenv('BASE_DIR', '/goloop')
    temp_env['ONLY_GOLOOP'] = converter.str2bool(os.getenv('ONLY_GOLOOP', False))
    return temp_env


def set_docker_compose(home_path:str):
    docker_compose = {
        'version': '3',
        'services': {
            'icon2-node': {
                'image': 'iconloop/goloop-icon:latest',
                'container_name': 'icon2-node',
                'restart': 'on-failure',
                'network_mode': 'host',
                'environment': {
                    'GENESIS_STORAGE': '/goloop/config/icon_genesis.zip',
                    'MAX_BLOCK_TX_BYTES': '2048000',
                    'NORMAL_TX_POOL': '10000',
                    'ROLE': '0',
                    'GOLOOP_ENGINES': 'python',
                    'GOLOOP_P2P_LISTEN': ':7100',
                    'GOLOOP_RPC_DUMP': 'false',
                    'GOLOOP_CONSOLE_LEVEL': 'debug',
                    'GOLOOP_LOG_LEVEL': 'trace',
                    'GOLOOP_LOGFILE': '/goloop/logs/goloop.log',
                    'GOLOOP_LOG_WRITER_FILENAME': '/goloop/logs/goloop.log',
                    'GOLOOP_LOG_WRITER_COMPRESS': 'true',
                    'GOLOOP_LOG_WRITER_LOCALTIME': 'true',
                    'GOLOOP_LOG_WRITER_MAXAGE': '0',
                    'GOLOOP_LOG_WRITER_MAXSIZE': '1024',
                    'GOLOOP_LOG_WRITER_MAXBACKUPS': '7',
                    'SEEDS': 'seed.ctz.solidwallet.io:7100',
                    'GOLOOP_P2P': '52.78.213.121:7100',
                    'GOLOOP_RPC_ADDR': ':9000',
                    'CID': '0x1'
                },
                'cap_add': ['SYS_TIME'],
                'volumes': ['./config:/goloop/config',
                          './data:/goloop/data',
                          './logs:/goloop/logs']
            }
        }
    }
    _url = "http://checkip.amazonaws.com"
    os.system(f"mkdir -p {home_path}/goloop/config")
    with urlopen(_url) as res:
        public_ip = res.read().decode().replace('\n', '')
    port = docker_compose['services']['icon2-node']['environment'].get('GOLOOP_P2P_LISTEN', ':8080').split(':')[-1]
    docker_compose['services']['icon2-node']['environment']['GOLOOP_P2P'] = f"{public_ip}:{port}"
    with open(f"{home_path}/goloop/docker-compose.yml", 'w') as outfile:
        yaml.dump(docker_compose, outfile)
    os.system(f"curl -o {home_path}/goloop/config/icon_genesis.zip https://networkinfo.solidwallet.io/icon2/MainNet/icon_genesis.zip")
    return docker_compose


def remove_goloop_settings(home_path:str):
    os.system(f"rm -rf {home_path}/goloop")


def get_goloop_env():
    docker_compose = set_docker_compose()
    return docker_compose['services']['icon2-node']['environment']


def goloop_chain_join():
    return f"docker exec -it icon2-node goloop chain join " \
           f"--platform icon " \
           f"--channel icon_dex " \
           f"--genesis /goloop/config/icon_genesis.zip " \
           f"--tx_timeout 60000 " \
           f"--node_cache small " \
           f"--normal_tx_pool 10000 " \
           f"--db_type rocksdb " \
           f"--role 0 " \
           f"--seed seed.ctz.solidwallet.io:7100"


def goloop_chain_start():
    return f"docker exec -it icon2-node goloop chain start icon_dex"


def goloop_chain_leave():
    return f"docker exec -it icon2-node goloop chain leave icon_dex"


def goloop_chain_ls():
    return f"docker exec -it icon2-node goloop chain ls"