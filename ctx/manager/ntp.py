#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
import os
import sys
import time
import asyncio
import subprocess

from datetime import datetime
from config.configure import Configure as CFG


class NTPDaemon:
    def __init__(self, ):
        self.chk = re.compile(r'(0\.\d+)')
        self.date_chk = re.compile(r'(\d{8})')
        self.cfg = CFG(use_file=True)
        self.config = self.cfg.config
        self.cfg.logger = self.cfg.get_logger('health.log')
        self.check_time = self.set_check_time()

    def set_check_time(self, ):
        if isinstance(os.getenv('NTP_REFRESH_TIME'), int):
            return os.getenv('NTP_REFRESH_TIME')
        else:
            try:
                return int(os.getenv('NTP_REFRESH_TIME').strip())
            except Exception as e:
                self.cfg.logger.info("Set the NTP_REFRESH_TIME setting to the default 180.")
                return 180

    def localtime(self, ):
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

    def utctime(self, ):
        return datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

    async def sync_time(self, ):
        self.cfg.logger.info("NTP_SYNC Start")
        while True:
            self.cfg.logger.info(f"Local Time : {self.localtime()}")
            self.cfg.logger.info(f"UTC Time   : {self.utctime()}")
            best_ntp = self.config['settings']['env'].get('NTP_SERVER', False)
            if best_ntp is False:
                best_ntp = self.compare_ntp()[0][0]
            self.cfg.logger.info(f"Best NTP Server is {best_ntp}")
            try:
                code = os.system(f"ntpdate {best_ntp}")
                if int(code) == 0:
                    self.cfg.logger.info("Time sync success!")
                else:
                    self.cfg.logger.error("Failed! Check NTP Server or Your Network or SYS_TIME permission.")
            except Exception as e:
                self.cfg.logger.error("Failed! Check NTP daemon.")
            await asyncio.sleep(self.check_time * 60)

    def compare_ntp(self, ):
        if self.config['settings']['env'].get('NTP_SERVERS'):
            ntp_servers = self.config['settings']['env'].get('NTP_SERVERS')
        else:
            ntp_servers = self.config['settings']['env']['COMPOSE_ENV'].get('NTP_SERVERS')
        cmd = "nmap -sU -p 123 " + " ".join(ntp_servers.split(",")) + " | grep up -B 1"
        self.cfg.logger.info(f"compare_cmd={cmd}")
        rs, _ = self.ntp_run(cmd)
        rs_dict = dict()
        for i, r in enumerate(rs):
            for ntp in self.config['settings']['env'].get('NTP_SERVERS').split(","):
                if ntp in r:
                    if len(rs) == i+1:
                        break
                    rs_dict[ntp] = float(re.findall(self.chk, rs[i+1])[0])
        self.cfg.logger.info("NTP Rank")
        for key, val in rs_dict.items():
            self.cfg.logger.info(f"{key} - {val}")
        return sorted(rs_dict.items(), key=(lambda x: x[1]))

    def ntp_run(self, cmd):
        rs = subprocess.check_output(cmd, shell=True, encoding='utf-8').split('\n')
        code = subprocess.check_output("echo $?", shell=True, encoding='utf-8').split('\n')
        return rs, code

    def run(self, ):
        self.sync_time()


if __name__ == "__main__":
    time.sleep(5)
    ND = NTPDaemon()
    ND.run()
