#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
import os
import time
import asyncio
import subprocess
import ntplib

from datetime import datetime
from config.configure import Configure as CFG
from devtools import debug
from pawnlib.typing import const


class NTPDaemon:
    def __init__(self, sleep_unit="minutes",):
        self.chk = re.compile(r'(0\.\d+)')
        self.date_chk = re.compile(r'(\d{8})')
        self.cfg = CFG(use_file=True)
        self.config = self.cfg.config
        self.cfg.logger = self.cfg.get_logger('health.log')
        self.sleep_unit = sleep_unit
        self.sleep_time = 1
        self._default_refresh_time = 180
        self._ntp_refresh_time = os.getenv('NTP_REFRESH_TIME', self._default_refresh_time).strip()

        self.set_check_time()

    def set_check_time(self, ):
        _sleep_unit_dict = {
            "hours": const.HOUR_IN_SECONDS,
            "minutes": const.MINUTE_IN_SECONDS,
            "seconds": 1,
        }
        _ntp_refresh_time = 0
        if isinstance(self._ntp_refresh_time, int) and int(self._ntp_refresh_time) > 0:
            _ntp_refresh_time = self._ntp_refresh_time
        else:
            try:
                _ntp_refresh_time = int(self._ntp_refresh_time)
            except Exception as e:
                self.cfg.logger.info(f"Set the NTP_REFRESH_TIME setting to the default {self._default_refresh_time}. - {e}")
                _ntp_refresh_time = self._default_refresh_time
        self.sleep_time = _ntp_refresh_time * _sleep_unit_dict.get(self.sleep_unit, 1)

    @staticmethod
    def localtime():
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

    @staticmethod
    def utctime():
        return datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

    async def sync_time(self, ):
        while True:
            best_ntp = self.cfg.get_base_config('NTP_SERVER')
            if not best_ntp:
                try:
                    best_ntp = self.get_best_ntp_server()
                except Exception as e:
                    self.cfg.logger.error(f"[NTP] got error best_ntp = {e}")
                    best_ntp = None
                if best_ntp:
                    self.cfg.logger.info(f"[NTP] Best responsive NTP server is [ {best_ntp} ]")
                else:
                    self.cfg.logger.error(f"[NTP][ERROR] Cannot found NTP servers. NTP_SERVERS={self.config.get('NTP_SERVERS', None)}")

            if best_ntp:
                self.run_sync_command(best_ntp)

            await asyncio.sleep(self.sleep_time)

    def run_sync_command(self, best_ntp=None):
        self.cfg.logger.info(f"[NTP] Time synchronization Start. ({best_ntp}), NTP_REFRESH_TIME={self.sleep_time}sec")
        self.cfg.logger.debug(f"[NTP] NTP_REFRESH_TIME={self._ntp_refresh_time}, sleep_time={self.sleep_time}, sleep_unit={self.sleep_unit}")
        try:
            code = os.system(f"ntpdate -u {best_ntp}")
            if int(code) == 0:
                self.cfg.logger.info(f"[NTP] Local Time : {self.localtime()}")
                self.cfg.logger.info(f"[NTP] UTC Time   : {self.utctime()}")
                self.cfg.logger.info("[NTP] Time synchronization succeeded!")
            else:
                self.cfg.logger.error(f"[NTP] Failed! Check NTP Server or Your Network or SYS_TIME permission. return code={code}")
        except Exception as e:
            self.cfg.logger.error(f"[NTP] Failed! Check NTP daemon. {e}")

    def get_best_ntp_server(self, ):
        ntp_servers = self.cfg.get_base_config('NTP_SERVERS')
        min_res_time = None
        selected_server = None
        if ntp_servers:
            self.cfg.logger.info(f"[NTP] NTP Server list : {ntp_servers.split(',')}")
            for ntp_server in ntp_servers.split(","):
                try:
                    client = ntplib.NTPClient()
                    res = client.request(ntp_server, version=3, timeout=1)
                    res_time = res.tx_time - res.orig_time
                    self.cfg.logger.debug(f"[NTP] {ntp_server:<20s}: {res_time:.3f} s")
                    if min_res_time is None or res_time < min_res_time:
                        min_res_time = res_time
                        selected_server = ntp_server
                except:
                    self.cfg.logger.error(f"[NTP] {ntp_server} is unresponsive or has timed out")

            return selected_server
        else:
            self.cfg.logger.error(f"[NTP] ntp_servers is none, env={self.config.get('NTP_SERVERS')}, "
                                  f"COMPOSE_ENV={self.config.get('NTP_SERVERS')}")

    def ntp_run(self, cmd):
        rs = subprocess.check_output(cmd, shell=True, encoding='utf-8').split('\n')
        code = subprocess.check_output("echo $?", shell=True, encoding='utf-8').split('\n')
        return rs, code

    async def run(self, ):
        await self.sync_time()


if __name__ == "__main__":
    time.sleep(5)
    ND = NTPDaemon()
    ND.run()
