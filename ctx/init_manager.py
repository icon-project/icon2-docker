#!/usr/bin/with-contenv python3
# -*- coding: utf-8 -*-
import os
import sys
import socket

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.configure import Configure as CFG
from config.configure_setter import ConfigureSetter as CS
from common import resources
from pawnlib.utils.notify import send_slack
from pawnlib.config import pawn


class InitManager:
    def __init__(self, ):
        self.cfg = CFG()  # Configure
        if self.cfg.base_env['ONLY_GOLOOP'] is False:
            self.cs = CS()  # ConfigureSetter

    def run(self, ):
        self.print_banner()
        self.print_resources()
        self.cfg.logger.info("[INIT_CONFIG] Initializing Configuration")
        self._send_slack("Starting Node")
        self.print_config()
        self.check_fs_permissions()

        self.cs.check_server_environment_prepare()

        self.cs.create_yaml_file()
        self.cs.create_env_file()
        self.cs.make_base_dir()
        self.cs.create_key()
        self.cs.create_genesis_json()
        self.cs.create_gs_zip()
        self.cs.create_icon_config()
        self.cs.create_db()
        self.cfg.logger.info("----- Finish initializing ---")
        # self.cs.validate_env()

    def print_config(self):
        self._print_dict_items(self.cfg.base_env, "[INIT_CONFIG]")

        ip_type = self._check_ip_type()
        self.cfg.logger.info(f"[INIT_CONFIG] GOLOOP_P2P = \"{self.cfg.config['GOLOOP_P2P']}\" ({ip_type})")

        if self.cfg.config:
            ctx_config = {k: v for k, v in self.cfg.config.items() if not k.startswith("GOLOOP")}
            goloop_config = {k: v for k, v in self.cfg.config.items() if k.startswith("GOLOOP") and v is not None}

            # mask the password and secrets
            masked_configs = ['KEY_PASSWORD', 'SLACK_WH_URL']
            for config_key in masked_configs:
                if config_key in ctx_config and len(ctx_config[config_key]):
                    ctx_config[config_key] = '*' * len(str(ctx_config[config_key]))

            self._print_dict_items(dict_obj=ctx_config, prefix="[CTX]")
            self._print_dict_items(dict_obj=goloop_config, prefix="[GOLOOP]")

    def _print_dict_items(self, dict_obj, prefix):
        for key, value in dict_obj.items():
            self.cfg.logger.info(f"{prefix} {key} = {value} ({type(value).__name__})")

    def _send_slack(self, title="", msg_level='info'):
        try:
            send_slack(
                url=self.cfg.config['SLACK_WH_URL'],
                msg_text=self.cfg.export_major_config(),
                title=title,
                msg_level=msg_level
            )
        except:
            pass

    def _check_ip_type(self):
        if self.cfg.base_env.get('LOCAL_TEST') is True:
            ip_type = "LOCAL_TEST"
        else:
            ip_type = "PUBLIC"
        return ip_type

    def check_fs_permissions(self):
        goloop_data_dir = self.cfg.config.get('GOLOOP_NODE_DIR')
        goloop_log_dir = self.cfg.config.get('LOGDIR')
        prefix_log = "[PERM_CHECK]"
        # prefix_error_log = f"{prefix_log}[ERROR]"
        is_permission = True
        for directory in [goloop_data_dir, goloop_log_dir]:
            if not self.check_can_write_to_directory(directory, prefix=prefix_log):
                is_permission = False

        if not self.check_can_create_socket(f"{goloop_data_dir}/__check_can_create_socket.sock", prefix=prefix_log):
            is_permission = False

        if is_permission:
            self.cfg.logger.info(f"{prefix_log} All file system permission checks passed.")
        else:
            # self.cfg.logger.error(f"{prefix_error_log} One or more file system permission checks failed.")
            self.cfg.handle_value_error(f"{prefix_log} One or more file system permission checks failed.")

    def check_can_write_to_directory(self, directory, prefix=""):
        """
        Check if the current process has write access to the given directory.

        :param directory: The path of the directory to check.
        :param prefix:
        :return: True if the current process has write access to the directory, False otherwise.
        """
        if os.access(directory, os.W_OK):
            return True
        else:
            self.cfg.handle_value_error(f"{prefix} Can't write to directory '{directory}'")
            return False

    def check_can_create_socket(self, socket_path, prefix=""):
        """
        Check if the current process can create a Unix domain socket at the given path.

        https://github.com/docker/for-mac/issues/6651
        The directory shared with VirtioFS has a problem with socket read.

        :param socket_path: The path where to create the socket.
        :param prefix:
        :return: True if the current process can create a socket at the path, False otherwise.
        """

        if os.path.exists(socket_path):
            try:
                os.remove(socket_path)
            except OSError as e:
                self.cfg.handle_value_error(f"{prefix} Cannot remove existing file at '{socket_path}': {str(e)}")
                return False

        try:
            server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            server.bind(socket_path)
            if not os.path.exists(socket_path):
                self.cfg.handle_value_error(f"{prefix} Socket file '{socket_path}' was not created.")
                return False

            server.close()
            os.unlink(socket_path)  # Clean up after ourselves.

            # pawn.console.log("[red] Created socket")
            return True
        except OSError as e:
            self.cfg.handle_value_error(f"{prefix} Cannot create a socket at {socket_path}: {str(e)}")
            return False

    def check_file_access(self, file_path, prefix=""):
        """
        Check if the current process can access a file at the given path.

        :param file_path: The path of the file to check.
        :param prefix:
        :return: True if the current process can access the file, False otherwise.
        """

        try:
            # Try to open and close the file.
            with open(file_path) as f:
                pass
            return True
        except OSError as e:
            self.cfg.handle_value_error(f"{prefix} Cannot access {file_path}: {str(e)}")
            return False

    def print_banner(self):
        v_info = self.cfg.get_version()
        config_version = self.cfg.config.get('config_version')

        self.cfg.logger.info(f" ██████╗████████╗██╗  ██╗ Goloop Version: {v_info.get('VERSION')}")
        self.cfg.logger.info(f"██╔════╝╚══██╔══╝╚██╗██╔╝ Python Version: {v_info.get('PYTHON_VERSION')}")
        self.cfg.logger.info(f"██║        ██║    ╚███╔╝  CTX Version   : {v_info.get('VCS_REF')}")
        self.cfg.logger.info(f"██║        ██║    ██╔██╗  Config Version: {config_version}")
        self.cfg.logger.info(f"╚██████╗   ██║   ██╔╝ ██╗ Build Date    : {v_info.get('BUILD_DATE')}")
        self.cfg.logger.info(f" ╚═════╝   ╚═╝   ╚═╝  ╚═╝ NTP Version   : {v_info.get('NTP_VERSION')}")

    def print_resources(self):
        try:
            self.cfg.logger.info(f"[RESOURCES] System Information: {resources.get_platform_info()}")
            self.cfg.logger.info(f"[RESOURCES] Memory Information: {resources.get_mem_info(unit='GB')}")
            self.cfg.logger.info(f"[RESOURCES] rlimit Information: {resources.get_rlimit_nofile()}")
        except Exception as e:
            self.cfg.logger.error(f"get resource error - {e}")


if __name__ == '__main__':
    IM = InitManager()
    if IM.cfg.base_env['ONLY_GOLOOP'] is False:
        IM.run()
