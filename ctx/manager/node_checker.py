#!/usr/bin/env python3
#-*- coding: utf-8 -*-
import sys
import socket
import asyncio
import requests
import subprocess
import socket_request

from concurrent import futures
from datetime import datetime
from ping3 import ping

from config.configure import Configure as CFG
from common.output import send_slack


class NodeChecker:
    def __init__(self, use_file=True):
        self.oc = OSChecker()
        self.pc = PeerChecker()
        self.cfg = CFG(use_file=use_file)
        self.config = self.cfg.config
        self.unix_socket = self.config.get("GOLOOP_NODE_SOCK", "/goloop/data/cli.sock")
        self.ctl = socket_request.ControlChain(unix_socket=self.unix_socket)
        self.cfg.logger = self.cfg.get_logger('health.log')

    def get_peer_goloop(self, peer_info):
        temp_dict = dict()
        temp_dict['cid'] = peer_info.get('cid', None)
        temp_dict['nid'] = peer_info.get('nid', None)
        temp_dict['height'] = peer_info.get('height', None)
        temp_dict['channel'] = peer_info.get('channel', None)
        temp_dict['state'] = peer_info.get('state', None)
        return temp_dict

    def result_formatter(self, log: str):
        return_str = f"[{datetime.today().strftime('%Y-%m-%d %H:%M:%S')}] {log}"
        return return_str

    def check_up_seeds(self, _p2p_port: int, _rpc_port: int):
        p2p_rs = list()
        rpc_rs = list()
        peer_ip_list = [addr.split(':')[0] for addr in self.config.get('SEEDS').split(',')]
        with futures.ThreadPoolExecutor() as executor:
            p2p_results = [
                executor.submit(self.oc.port, friend.split(':')[0], _p2p_port)
                for friend in peer_ip_list
            ]
            rpc_results = [
                executor.submit(self.oc.port, friend.split(':')[0], _rpc_port)
                for friend in peer_ip_list
            ]
        for i, f in enumerate(futures.as_completed(p2p_results)):
            if f.result() is False:
                p2p_rs.append(peer_ip_list[i])
        for i, f in enumerate(futures.as_completed(rpc_results)):
            if f.result() is False:
                rpc_rs.append(peer_ip_list[i])
        return p2p_rs, rpc_rs

    async def check_node(self, node_ip='localhost'):
        _block = [0, 0]
        _peer_stack = 0
        _block_stack = 0
        _stack_limit = int(self.config.get('CHECK_STACK_LIMIT'))
        _p2p_port = int(self.config.get('GOLOOP_P2P_LISTEN', '8080').split(':')[-1])
        _rpc_port = int(self.config.get('GOLOOP_RPC_ADDR', '9080').split(':')[-1])
        _endpoint = '/admin/chain/icon_dex'
        _check_peer_stack = self.config.get('CHECK_PEER_STACK', 6)
        _check_block_stack = self.config.get('CHECK_BLOCK_STACK', 10)
        _check_interval = self.config.get('CHECK_INTERVAL', 10)
        _check_timeout = self.config.get('CHECK_TIMEOUT', 10)
        while True:
            peer_rs = self.pc.peer_status(f"http://{node_ip}:{_rpc_port}{_endpoint}", self.config.get('CHECK_TIMEOUT', _check_timeout))
            if not peer_rs:
                _peer_stack += 1
                if not _peer_stack % self.config.get('CHECK_PEER_STACK', _check_peer_stack):
                    self.cfg.logger.error(f"Node API=Failed,stack_count={_peer_stack},Time={int(_peer_stack) * int(self.config.get('CHECK_PEER_STACK', _check_peer_stack))} sec)")
                    if self.config.get('SLACK_WH_URL'):
                        send_slack(self.config['SLACK_WH_URL'],
                                   self.result_formatter(f"Node API response=Failed,Stack count={_peer_stack},Time={int(_peer_stack) * int(self.config.get('CHECK_PEER_STACK', _check_peer_stack))} sec)"),
                                   'Node health',
                                   msg_level='error'
                                   )
            else:
                self.cfg.logger.info(f"Node API response={self.get_peer_goloop(peer_rs)}")
                if _peer_stack >= self.config.get('CHECK_PEER_STACK', _check_peer_stack):
                    self.cfg.logger.info(f"Node API=OK,stack_count={_peer_stack},Time={int(_peer_stack) * int(self.config.get('CHECK_PEER_STACK', _check_peer_stack))} sec)")
                    if self.config.get('SLACK_WH_URL'):
                        send_slack(self.config['SLACK_WH_URL'],
                                   self.result_formatter(f"Node API response=OK,Stack count={_peer_stack},Time={int(_peer_stack) * int(self.config.get('CHECK_PEER_STACK', _check_peer_stack))} sec)"),
                                   'Node health',
                                   msg_level='info'
                                   )
                _peer_stack = 0
                _block[-1] = peer_rs.get('height', 0)
                if _block[-1] <= _block[0]:
                    _block_stack += 1
                    if not _block_stack % self.config.get('CHECK_BLOCK_STACK', _check_block_stack):
                        self.cfg.logger.error(f"Node block_sync=Failed,stack_count={_block_stack},block_height={_block[-1]})")
                        if self.config.get('SLACK_WH_URL'):
                            if self.config.get('CHECK_SEEDS'):
                                p2p_rs, rpc_rs = self.check_up_seeds(_p2p_port, _rpc_port)
                                if p2p_rs:
                                    self.cfg.logger.warning(f"Node check_up_seeds(p2p)={p2p_rs}")
                                if rpc_rs:
                                    self.cfg.logger.warning(f"Node check_up_seeds(rpc)={rpc_rs}")
                            send_slack(self.config['SLACK_WH_URL'],
                                       self.result_formatter(f"Node block_sync=Failed,stack_count={_block_stack},block_height={_block[-1]})"),
                                       'Node block',
                                       msg_level='error'
                                       )
                    _block[0] = _block[-1]
                else:
                    if _block_stack >= self.config.get('CHECK_BLOCK_STACK', _check_block_stack):
                        self.cfg.logger.info(f"Node block_sync=OK,stack_count={_block_stack},block_height={_block[-1]})")
                        if self.config.get('SLACK_WH_URL'):
                            send_slack(self.config['SLACK_WH_URL'],
                                       self.result_formatter(f"Node block_sync=OK,Stack count={_block_stack},Block={_block[-1]})"),
                                       'Node block',
                                       msg_level='info'
                                       )
                    _block_stack = 0
                    _block[0] = _block[-1]
            if _peer_stack >= _stack_limit or _block_stack >= _stack_limit:
                self.cfg.logger.error(f"Node stack_limit over. PEER STACK={_peer_stack}, BLOCK STACK={_block_stack}, Block={_block[-1]}")
                if self.config.get('SLACK_WH_URL'):
                    send_slack(self.config['SLACK_WH_URL'],
                               self.result_formatter(f"Node stack_limit over. PEER STACK={_peer_stack}, BLOCK STACK={_block_stack}, Block={_block[-1]})"),
                               'Node shutdown',
                               msg_level='warning'
                               )
                sys.exit(127)
            await asyncio.sleep(self.config.get('CHECK_TIMEOUT', _check_interval))

    def run(self, ):
        self.check_node()


class OSChecker:
    def __init__(self, ):
        pass

    def name(self, ):
        return subprocess.check_output('hostname', shell=True).decode().split('\n')[0]

    def live(self, host, timeout=5):
        result_ping = ping(host, timeout=timeout)
        return result_ping if result_ping else 0.0

    def disk(self, ):
        pass

    def memory(self, ):
        pass

    def port(self, address, port):
        a_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        location = (address, port)
        result_of_check = a_socket.connect_ex(location)
        if result_of_check == 0:
            return_val = True
        else:
            return_val = False
        a_socket.close()
        return return_val


class PeerChecker:
    def __init__(self, ):
        pass

    def peer_status(self, url, timeout=3):
        try:
            res = requests.get(url, timeout=timeout)
        except:
            return {}
        else:
            if res and res.status_code == 200:
                res = res.json()
                if isinstance(res, list):
                    res = res[0]
            return res


if __name__ == '__main__':
    NC = NodeChecker(use_file=False)
    NC.run()
