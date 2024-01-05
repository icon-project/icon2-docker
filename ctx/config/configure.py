#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import json
import yaml
import requests
import socket

from common.logger import CustomLog as CL
import logging
from logging.handlers import TimedRotatingFileHandler
from common import converter
from termcolor import cprint
from devtools import debug
from pawnlib.typing import Null
from pawnlib.utils.notify import send_slack, send_slack_token
from pawnlib.config import pawn
from pawnlib.typing import str2bool, is_valid_ipv4


def singleton(class_):
    instances = {}

    def getinstance(*args, **kwargs):
        if class_ not in instances:
            instances[class_] = class_(*args, **kwargs)
        return instances[class_]
    return getinstance


@singleton
class Configure:
    def __init__(self, use_file=False, use_exception_handler=True):
        self.about = {}
        self.get_version()
        self.config = dict()
        self.second_env_dict = {
            "GOLOOP_BACKUP_DIR": "backup",
            "GOLOOP_EE_SOCKET": "ee.sock",
            "GOLOOP_NODE_SOCK": "cli.sock",
            "GOLOOP_CPUPROFILE": "cpu.profile",
            "GOLOOP_MEMPROFILE": "mem.profile"
        }
        self.base_env = self._base_env()
        self.log_dir = f"{self.base_env['BASE_DIR']}/logs"
        if not os.path.isdir(self.log_dir):
            os.mkdir(self.log_dir)

        self.loggers = {'booting.log': self.init_logger('booting.log', log_level=self.base_env['CTX_LEVEL'], log_stdout=True)}
        self.logger = self.get_logger('booting.log')

        if pawn.get('PAWN_DEBUG'):
            pawn.error_logger = self.logger

        if self.base_env['ONLY_GOLOOP'] is True:
            self.load_offline_config()
            return

        self.get_config(use_file=use_file)

        if use_exception_handler:
            sys.excepthook = self.exception_handler

    def get_version(self):
        for version_info in ["VERSION", "BUILD_DATE", "VCS_REF", "PYTHON_VERSION", "NTP_VERSION", ]:
            self.about[version_info] = os.getenv(version_info)
        return self.about

    def exception_handler(self, exception_type, exception, traceback):
        exception_string = f"[Exception] {exception_type.__name__}: {exception}, {traceback.tb_frame}"
        cprint(f"{exception_string}", "red")
        ignore_exceptions = ["KeyboardInterrupt"]
        is_send = not any(exp_keyword in exception_string for exp_keyword in ignore_exceptions)
        self.logger.error(f"{exception_string}, is_send={is_send}")
        if is_send:
            try:
                self.send_auto_slack(
                    msg_text=exception_string,
                    title='Exception error',
                    msg_level='error'
                )
            except:
                pass

        if self.base_env.get('CTX_LEVEL') == "debug":
            trace = []
            tb = exception.__traceback__
            while tb is not None:
                trace.append({
                    "filename": tb.tb_frame.f_code.co_filename,
                    "name": tb.tb_frame.f_code.co_name,
                    "reason": tb.tb_frame.f_code,
                    "lineno": tb.tb_lineno
                })
                debug(tb.tb_frame)
                tb = tb.tb_next
            debug({
                'type': type(exception).__name__,
                'message': str(exception),
                'trace': trace
            })

    def export_major_config(self):
        _major_base_keys = ["SERVICE", "USE_HEALTH_CHECK",  "USE_NTP_SYNC"]
        _major_config_keys = ["CID", "ROLE", "CHECK_BLOCK_STACK", "CHECK_INTERVAL", "CHECK_PEER_STACK", "CHECK_STACK_LIMIT", "CHECK_TIMEOUT"]
        _cfg_config = {}

        for key in _major_base_keys:
            _cfg_config[key] = self.base_env.get(key)

        for key in _major_config_keys:
            _cfg_config[key] = self.config.get(key)

        return _cfg_config

    def load_offline_config(self):
        _major_base_keys = ["SERVICE", "USE_HEALTH_CHECK",  "USE_NTP_SYNC"]
        _major_config_keys = ["CID", "ROLE", "CHECK_BLOCK_STACK", "CHECK_INTERVAL", "CHECK_PEER_STACK", "CHECK_STACK_LIMIT", "CHECK_TIMEOUT"]
        _env_keys = ["SLACK_WH_URL"]

        _major_config = {
            "base_env": {
                "SERVICE": "",
                "USE_HEALTH_CHECK": {
                    "default": True,
                    "type": str2bool
                },
                "USE_NTP_SYNC": {
                    "default": True,
                    "type": str2bool,
                },
                "ONLY_GOLOOP": {
                    "default": False,
                    "type": str2bool,
                }
            },
            "config": {
                "CID": "",
                "ROLE": "",
                "CHECK_BLOCK_STACK":  {
                    "default": 10,
                    "type": int,
                },
                "CHECK_INTERVAL": {
                    "default": 10,
                    "type": int,
                },
                "CHECK_PEER_STACK": {
                    "default": 6,
                    "type": int,
                } ,
                "CHECK_STACK_LIMIT": {
                    "default": 360,
                    "type": int,
                },
                "CHECK_TIMEOUT": {
                    "default": 10,
                    "type": int,
                },
                "SLACK_WH_URL": "",
                # "SLACK_TOKEN": "",
                # "SLACK_CHANNEL": "",
            }
        }
        for config_key, config in _major_config.items():
            for config_name, config_value in config.items():
                _config_value = None
                _env_value = os.getenv(config_name, None)
                if isinstance(config_value, dict) and config_value.get('type'):
                    if not _env_value:
                        _config_value = config_value.get('default')
                    else:
                        _config_value = config_value['type'](_env_value)
                else:
                    _config_value = _env_value
                pawn.console.debug(f"{config_name}={_config_value} ({type(_config_value).__name__})")
                getattr(self, config_key, )[config_name] = _config_value

    def send_auto_slack(self, title="", msg_text="", msg_level="info", url=None):

        pawn.console.debug(f"Try to send SLACK, SLACK_WH_URL={self.config.get('SLACK_WH_URL')}")
        _slack_token = os.getenv('SLACK_TOKEN', None)
        _slack_channel = os.getenv('SLACK_CHANNEL', None)
        # _slack_token = self.config.get('SLACK_TOKEN')
        # _slack_channel = self.config.get('SLACK_CHANNEL')

        if _slack_token and _slack_channel:
            send_slack_token(
                token=_slack_token,
                channel_name=_slack_channel,
                title=title,
                msg_level=msg_level,
                message=msg_text,
                send_user="CTX"
            )

        if self.config.get('SLACK_WH_URL'):
            try:
                send_slack(
                    url=self.config['SLACK_WH_URL'],
                    msg_text=msg_text,
                    title=title,
                    msg_level=msg_level
                )
            except Exception as e:
                self.logger.error(f"Failed to send SLACK - {e}")

    def get_logger(self, log_file="booting.log"):
        return self.loggers.get(log_file, self.loggers.get('booting.log')).log

    def init_logger(self, log_file=None, log_level='debug', log_stdout=False):
        logger = CL(log_file.upper())
        logger.set_level(log_level.upper())
        if log_stdout or self.config.get('DOCKER_LOG_STDOUT', False) is True:
            # logger.stream_handler(log_level.upper())
            logger.add_rich_handler(log_level.upper())

        logger.time_rotate_handler(
            filename=f"{self.log_dir}/{log_file}",
            when="midnight",
            backup_count=6,
            level=log_level.upper()
        )
        logger.set_level(log_level.upper())
        logger.error_file_handler(f"{self.log_dir}/error.log")

        return logger

    def _base_env(self, ):
        temp_env = dict()
        temp_env['CONFIG_URL'] = os.getenv('CONFIG_URL', 'https://networkinfo.solidwallet.io/node_info')
        temp_env['SERVICE'] = os.getenv('SERVICE', 'MainNet')
        temp_env['CONFIG_URL_FILE'] = os.getenv('CONFIG_URL_FILE', 'default_configure.yml')
        temp_env['CONFIG_LOCAL_FILE'] = os.getenv('CONFIG_LOCAL_FILE', '/goloop/configure.yml')
        temp_env['LOCAL_TEST'] = converter.str2bool(os.getenv('LOCAL_TEST', False))
        temp_env['BASE_DIR'] = os.getenv('BASE_DIR', '/goloop')
        temp_env['ONLY_GOLOOP'] = converter.str2bool(os.getenv('ONLY_GOLOOP', False))
        temp_env['CTX_LEVEL'] = self._get_validated_environment("CTX_LEVEL", "info", ["info", "debug", "warn"])

        temp_env['ENABLE_VALIDATION'] = converter.str2bool(os.getenv('ENABLE_VALIDATION', True))
        temp_env['USE_HEALTH_CHECK'] = converter.str2bool(os.getenv('USE_HEALTH_CHECK', True))

        temp_env['USE_NTP_SYNC'] = converter.str2bool(os.getenv('USE_NTP_SYNC', True))
        temp_env['GOLOOP_KEY_STORE'] = os.getenv('GOLOOP_KEY_STORE', "/goloop/config/keystore.json")
        temp_env['NTP_SERVERS'] = os.getenv('NTP_SERVERS', "time.google.com,time.cloudflare.com,time.facebook.com,time.apple.com,time.euro.apple.com")
        temp_env['NTP_SERVER'] = os.getenv('NTP_SERVER', None)
        temp_env['DOWNLOAD_OPTION'] = os.getenv('DOWNLOAD_OPTION', None)
        # temp_env['ROLE'] = self._get_validated_environment("ROLE", "0", ["0", "1", "3"])
        return temp_env

    @staticmethod
    def _get_validated_environment(key=None, default=None, allows=[]):
        if key not in os.environ:
            pawn.console.debug(f"<WARN> '{key}' environment variable is not set.")
        _env_value = os.getenv(key, default)
        if allows and _env_value not in allows:
            raise ValueError(f"It's not allowed value for the '{key}' environment variable, input='{_env_value}', allows={allows} ")
        return _env_value

    def get_base_config(self, env_key):
        if self.config.get(env_key, '__NOT_DEFINED__') != '__NOT_DEFINED__':
            value = self.config.get(env_key)
        else:
            value = self.base_env.get(env_key, '__NOT_DEFINED__')
        return value

    def get_config(self, use_file):
        service_url = f'{self.base_env["CONFIG_URL"]}/{self.base_env["SERVICE"]}'
        # self.validate_environment()
        _config_version = None
        is_config_local_file = os.path.exists(self.base_env['CONFIG_LOCAL_FILE'])
        if is_config_local_file or use_file:
            self.logger.info(f"Load config_from_file. file_exists={is_config_local_file}, file={self.base_env['CONFIG_LOCAL_FILE']} ")
            self.config_from_file()
        else:
            config_url = f'{service_url}/{self.base_env["CONFIG_URL_FILE"]}'
            self.logger.info("-- Download new configuration ")
            res = requests.get(config_url)
            if res.status_code == 200:
                self.config = yaml.safe_load(res.text)
                # self.about['config_version'] = self.config.get('version')
                _config_version = self.config.get('version')

                if self.config.get('settings') and self.config['settings'].get('env'):
                    for compose_env in self.config['reference'].get('env').keys():
                        if os.getenv(compose_env, '__NOT_DEFINED__') != '__NOT_DEFINED__':
                            self.config['settings']['env'][compose_env] = self.get_os_env(compose_env)
                        else:
                            pass
                    self.config['settings']['env'].update(self.base_env)
                    # [icon2]
                    icon2_envs = [env for env in self.config['reference'].get('env').keys() if env.startswith("GOLOOP")]
                    for icon2_env in icon2_envs:
                        self.config['settings']['env'][icon2_env] = self.get_os_env(icon2_env)
                    self.config['settings']['env']['GOLOOP_NODE_DIR'] = os.path.join(self.base_env['BASE_DIR'], 'data')
                    self.set_second_env(self.config['settings']['env']['GOLOOP_NODE_DIR'])
                    # [keystore]
                    key_store_filename = self.config['settings']['env'].get("KEY_STORE_FILENAME", None)
                    if key_store_filename:
                        self.config['settings']['env']['GOLOOP_KEY_STORE'] = f"{self.config['settings']['env']['BASE_DIR']}/config/{key_store_filename}"
                    else:
                        self.config['settings']['env']['GOLOOP_KEY_STORE'] = os.getenv('GOLOOP_KEY_STORE')
                    # [network]
                    if self.base_env.get('LOCAL_TEST') is True:
                        private_ip = self.get_local_ip()
                        port = self.config['settings']['env'].get('GOLOOP_P2P_LISTEN', ':8080').split(':')[-1]
                        self.config['settings']['env']['GOLOOP_P2P'] = f"{private_ip}:{port}"
                    else:
                        if os.getenv('GOLOOP_P2P') and os.getenv('GOLOOP_P2P') != '127.0.0.1:8080':
                            self.config['settings']['env']['GOLOOP_P2P'] = os.getenv('GOLOOP_P2P')
                        else:
                            public_ip = self.get_public_ip()
                            port = self.config['settings']['env'].get('GOLOOP_P2P_LISTEN', ':8080').split(':')[-1]
                            self.config['settings']['env']['GOLOOP_P2P'] = f"{public_ip}:{port}"

                    if self.base_env.get('LOCAL_TEST'):
                        self.base_env.pop('LOCAL_TEST')
                else:
                    self.logger.error('No env.')
            else:
                self.logger.error(f'API status code is {res.status_code}. ({service_url}/{self.base_env["CONFIG_URL_FILE"]})')

            if not self.config:
                self.logger.error(f'No config file, \'{self.base_env.get("SERVICE")}\' is an invalid SERVICE name.')
                sys.exit(127)

            if self.base_env.get('CTX_LEVEL').lower() == 'debug':
                _debug = True
            else:
                _debug = False

            self.config = converter.UpdateType(self.config, self.logger, debug=_debug).check()
            self.config['config_version'] = _config_version
        self.force_config_with_env_variable()

    def force_config_with_env_variable(self):
        env_variable_keys = ["DOWNLOAD_OPTION"]
        for _env in env_variable_keys:
            self.config[_env] = os.getenv(_env, None)

    def handle_value_error(self, exception_message=""):
        if self.base_env.get('ENABLE_VALIDATION'):
            raise ValueError(exception_message)
        else:
            self.logger.error(f"[ERROR]{exception_message} / ENABLE_VALIDATION={self.base_env.get('ENABLE_VALIDATION')}")

    def get_public_ip(self):
        try:
            public_ip = requests.get("http://checkip.amazonaws.com", verify=False).text.strip()
            if is_valid_ipv4(public_ip):
                return public_ip
            else:
                self.logger.error(f"An error occurred while fetching Public IP address. Invalid IPv4 address - '{public_ip}'")

        except Exception as e:
            self.logger.error(f"An error occurred while fetching Public IP address - {e}")
            return ""

    def get_local_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('10.255.255.255', 1))
            ipaddr = s.getsockname()[0]
        except Exception:
            ipaddr = '127.0.0.1'
        finally:
            s.close()

        if is_valid_ipv4(ipaddr):
            return ipaddr
        else:
            self.logger.error("An error occurred while fetching Local IP address. Invalid IPv4 address")

        return ""

    def set_second_env(self, dir_name):
        for env_key, env_val in self.second_env_dict.items():
            if os.getenv(env_key) is not None:
                self.config['settings']['env'][env_key] = os.getenv(env_key)
            else:
                self.config['settings']['env'][env_key] = f"{os.path.join(dir_name, env_val)}"

    def get_os_env(self, env_key):
        if os.getenv(env_key) and os.getenv(env_key).lower() in ['true', 'false']:
            if os.getenv(env_key).lower() == 'true':
                return True
            else:
                return False
        else:
            return os.getenv(env_key, None)

    def config_from_file(self, ):
        try:
            base_dir = self.base_env.get('BASE_DIR', '/goloop')
            file_name = f"{os.path.join(base_dir, self.base_env.get('CONFIG_LOCAL_FILE', 'configure.yml'))}"
            with open(file_name, 'r') as js:
                self.config = yaml.safe_load(js)
            self.logger.info("Loaded config_from_file")
        except FileNotFoundError as e:
            pawn.console.debug(e)

    def run(self, ):
        print(json.dumps(self.config, indent=4))


if __name__ == '__main__':
    CFG = Configure()
    CFG.run()
