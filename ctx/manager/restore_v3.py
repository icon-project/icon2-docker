#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import re
import sys
import time
import json
import shutil
import hashlib
import inspect
import requests
import threading

from halo import Halo
from timeit import default_timer
from datetime import datetime
from multiprocessing.pool import ThreadPool

from common import converter, output, base
from common.converter import region_info as region_s3_info  # region config
from common.converter import region_cf_info, todaydate, get_size  # region config,
from config.configure import Configure
from manager.file_indexing import FileIndexer
from pawnlib.output import is_file

# sys.excepthook = output.exception_handler

# SSL Warnning
base.disable_ssl_warnings()

filename = __file__
get_filename = filename.split('/')[-1]


def line_info(return_type=None):
    """
    It returns the name of the function that called it

    :param return_type:
    :return: the value of the variable result_info.
    """
    # line number
    cf = inspect.currentframe()
    line_number = cf.f_back.f_lineno

    # Call to Function name
    func_name = cf.f_back.f_code.co_name

    if return_type == 'filename':
        result_info = f'{get_filename}'
    elif return_type == 'function' or return_type == 'func_name' or return_type == 'f_name':
        result_info = f'{func_name}'
    elif return_type == 'lineinfo' or return_type == 'linenum' or return_type == 'lineno':
        result_info = f'{line_number}'
    elif return_type == 'info_all' or return_type is None:
        result_info = f'{get_filename}({func_name}.{line_number})'
    else:
        result_info = f'{get_filename}({func_name}.{line_number})'

    return result_info


def log_print(msg, color=None, level=None):
    """
    It prints a message to the console, with a timestamp and a log level

    :param msg: The message to be printed
    :param color: The color of the text
    :param level: The level of the message
    """

    color = color if color else 'green'
    level = level if level else 'INFO'

    now_time = (datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3])
    output.cprint(f'[{now_time}] [{level:5}] | {msg}', color)


class Restore:
    def __init__(self,
                 db_path=None,  # .settings.icon2.GOLOOP_NODE_DIR
                 network="MainNet",  # .settings.env.SERVICE
                 send_url=None,  # 사용자 입력   /  없어도무방   .settings.env.RESTORE_SEND_URL
                 bucket_name_prefix="icon2-backup",  # 사용자 입력(docker 변수로 ) 없을 경우 Default 사용  : false
                 download_path='restore',  # Download directory | 사용자 입력(docker 변수로) 없을 경우 defaut 사용  : false
                 download_url='download.solidwallet.io',  # Downlaod URL
                 download_url_type='s3',  # Download type check  s3 or cloud front , Default : s3
                 download_tool='axel',  # Download Tool command option .  Default Axel command  [ axel | aria2(aria2c)]
                 download_force=False,  # Download file이 동일할 경우에 대한 액션 True일 경우 모두 삭제 후 download /
                 download_option=None,
                 # False일 경우 동일 파일 비교 후 다를 경우 삭제 |  사용자 입력(docker 변수로 ) 없을 경우 default 사용  : false
                 ):
        """
        Restore is a class that restores a database from a backup file

        :param db_path: .settings.icon2.GOLOOP_NODE_DIR
        :param network: .settings.env.SERVICE
        :param send_url: 사용자 입력 /없어도 무방   .settings.env.RESTORE_SEND_URL
        :param bucket_name_prefix: 사용자 입력(docker 변수로 ) 없을 경우 default 사용  : false
        :param download_path: Download directory | 사용자 입력(docker 변수로) 없을 경우 defaut 사용  : false
        :param download_url: Download URL
        :param download_url_type: Download type check  s3 or cloud front , Default : s3 download" or "file_list"
        :param download_tool: Download Tool command option.  Default Axel command  [ axel | aria2(aria2c) ]
        :param download_force: Download file이 동일할 경우에 대한 액션 True일 경우 모두 삭제 후 download
                               False일 경우 동일 파일 비교 후 다를 경우 삭제 |
                               사용자 입력(docker 변수로 ) 없을 경우 default 사용  : false
        """
        self.cfg = Configure()
        self.config = self.cfg.config
        self.base_log_dir = f"{self.config['BASE_DIR']}/logs"
        self.debug = self.config['CC_DEBUG'] if self.config.get('CC_DEBUG') else False

        self.dl_dict = {}
        self.url_addr = None
        self.s3_bkurl = None

        self.db_path = db_path  # 필수 Default => icon2 : /app/goloop
        self.network = network  # 필수  Blockchain  node network name
        self.bucket_name_prefix = bucket_name_prefix  # 필수

        self.download_path = download_path  # Change variable name restore_path to download_path
        self.download_filename = ""
        self.download_url_type = download_url_type
        self.download_force = download_force
        self.download_tool = download_tool  # Default axel
        self.download_option = download_option
        self.verbose = None
        self.restore_path = None

        self.checksum_result = {}

        self.checksum_value = None
        self.fail_result = {}
        self.dl_url = None
        self.f_dict = None
        self.match_keyword = None
        self.region_info = None
        self.script_exit = False

        if self.download_url_type == "indexing":
            self.download_url = download_url
        elif self.download_url_type == "file_list":
            self.download_url = "https://icon2-backup-kr.s3.ap-northeast-2.amazonaws.com/s3sync"
        else:
            self.download_url = re.sub('(http|https)://', '', download_url)

        # Send url check
        self.send_url = send_url  # 없어도 무방
        self.is_send = True if send_url else False

        # Icon2 node DB Path check
        if self.db_path is None or not output.is_file(self.db_path):
            raise ValueError(f"[RESTORE] [ERROR] db_path not found - '{self.db_path}'")

        self.cpu_count = os.cpu_count()
        self.used_disk_max_percent = 70

        # self.run()
        self.restore_path = os.path.join(self.db_path, self.download_path)
        self.create_directory(self.restore_path)

        self.log_files = {
            "download": f"{self.base_log_dir}/download.log",
            "download_error": f"{self.base_log_dir}/download_error.log",
        }

        self.stored_local_path = {
            "index_url": "",
            "checksum_url": "",
            "re_download_list": f"{self.restore_path}/re_download_file_list.txt",
            "restored_marks": f"{self.restore_path}/RESTORED",
            "retry_count": f"{self.restore_path}/RETRY",
            "restored_checksum_marks": f"{self.restore_path}/checksum_result.json"
        }
        self.is_overwrite_file = False
        self.retry_file_count = 0
        self.max_retry_count = 10

    def read_retry_count(self):
        retry_count_path = self.stored_local_path["retry_count"]
        return  self._read_retry_count(retry_count_path)

    def log_restore_initiation(self):
        """
        Logs the initial information when the restore process starts.
        """
        self.cfg.logger.info(
        f"[RESTORE] Initiation: DOWNLOAD_URL={self.download_url}, SERVICE={self.network}, "
        f"DOWNLOAD_URL_TYPE={self.download_url_type}, RESTORE_PATH={self.restore_path}, "
        f"Retry Allowed={self.check_if_in_max_retry()}, Current Retry Count={self.read_retry_count()}"
    )

    def is_first_download_attempt(self):
        """
        Checks if this is the first attempt to download the file.

        :return: True if this is the first attempt, False otherwise.
        """
        return self.read_retry_count() == 0

    def check_if_in_max_retry(self):
        retry_count = self.read_retry_count()
        if retry_count <= self.max_retry_count:
            self.cfg.logger.info(f"Max retries reached: {retry_count}/{self.max_retry_count}")
            return True
        return False

    def update_retry_count(self, success):
        """
        Updates the retry count based on the operation success.
        Resets to 0 if successful, otherwise increments the count.

        :param success: Boolean indicating the success of the operation.
        """
        retry_count_path = self.stored_local_path["retry_count"]

        if success:
            self._write_retry_count(retry_count_path, 0)
        else:
            current_count = self._read_retry_count(retry_count_path)
            self._write_retry_count(retry_count_path, current_count + 1)

    def _read_retry_count(self, path):
        """
        Reads the current retry count from a file.

        :param path: Path to the file containing the retry count.
        :return: The current retry count.
        """
        try:
            with open(path, 'r') as file:
                return int(file.read().strip())
        except (FileNotFoundError, ValueError):
            return 0  # Return 0 if the file does not exist or is empty

    def _write_retry_count(self, path, count):
        """
        Writes the retry count to a file.

        :param path: Path to the file where the retry count will be stored.
        :param count: The retry count to write.
        """
        with open(path, 'w') as file:
            file.write(str(count))

    def run(self):
        # Restore start.....
        self._prepare()

        self.cfg.logger.info(
            f"[RESTORE] DOWNLOAD_URL={self.download_url}, SERVICE={self.network}, "
            f"DOWNLOAD_URL_TYPE={self.download_url_type}, RESTORE_PATH={self.restore_path}, "
            f"Retry={self.check_if_in_max_retry()}, retry_count={self.read_retry_count()}")


        # if not self.check_if_in_max_retry():
        if self.read_retry_count() == 0:
            # 파일 다운로드 및 검증
            self.cfg.logger.info("[RESTORE] Start First download")
            self.update_retry_count(False)
            # self.update_retry_count(False)
            self.download()

        # 에러가 있는 경우 재다운로드 진행
        self.re_download_if_error()

    def re_download_if_error(self):
        self.check_downloaded_file()
        self.cfg.logger.info(f"[RESTORE] checksum_result={self.checksum_result.get('status')}, retry_count={self.read_retry_count()}, self.check_if_in_max_retry()={self.check_if_in_max_retry()}")
        if (self.checksum_result and self.checksum_result.get("status") == "FAIL") and self.check_if_in_max_retry():
            self.update_retry_count(False)
            self.cfg.logger.info("[RESTORE] Try the one more downloading")
            self.create_db_redownload_list()   # add by hnsong (2022.08.25)
            self.download(redownload=True)
            self.check_downloaded_file()

        if self.checksum_result.get("status") == "OK":
            output.write_file(self.stored_local_path['restored_marks'], todaydate('ms'))
        elif self.checksum_result.get("status") == "FAIL":
            self.cfg.logger.error(f'[RESTORE] [ERROR] File checksum error : {self.checksum_result.get("status")}')
            raise Exception("[RESTORE] [ERROR] File checksum error")

    def _prepare(self):
        if self.already_restore_check():
            exit()
        self.download_checksum_and_filelist()

    def download_checksum_and_filelist(self):
        # Creating a list of the values in the log_files dictionary.
        delete_old_list = list(self.log_files.values())
        delete_old_list.append(self.stored_local_path['re_download_list'])
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")

        for old_file in delete_old_list:
            if output.is_file(old_file):
                backup_file = f"{old_file}.{current_time}"
                self.cfg.logger.info(f"[RESTORE] Backup successful: {old_file} to {backup_file}")
                os.rename(old_file, backup_file)

        if self.is_overwrite_file or \
            not is_file(f"{self.restore_path}/checksum.json") or \
            not is_file(f"{self.restore_path}/file_list.txt"):

            download_info_url = f"{self.download_url}/{self.network}.json"
            download_info_res = requests.get(download_info_url)
            if download_info_res.status_code == 200:
                download_info = download_info_res.json()
                self.cfg.logger.info(f"[RESTORE] index_url={download_info.get('index_url')}")
                self.cfg.logger.info(f"[RESTORE] checksum_url={download_info.get('checksum_url')}")
                for url_name in ["index_url", "checksum_url"]:
                    self.download_write_file(url=download_info.get(url_name), path=self.restore_path)
                    self.stored_local_path[url_name] = self._get_file_locate(download_info.get(url_name))
            else:
                self.cfg.logger.error(f'[RESTORE] [ERROR] Invalid url or service name, url={download_info_res}, '
                                      f'status={download_info_res.status_code}')
        else:
            self.cfg.logger.info('[RESTORE] It will use the already existing files checksum.json and file_list.txt.')
            self.stored_local_path['index_url'] = f"{self.restore_path}/file_list.txt"
            self.stored_local_path['checksum_url'] = f"{self.restore_path}/checksum.json"

    def already_restore_check(self):
        restored_file = self.stored_local_path['restored_marks']
        checksum_result_file = self.stored_local_path['restored_checksum_marks']
        check_stat = None

        if output.is_file(checksum_result_file):
            with open(checksum_result_file, 'r') as f:
                check_stat = json.load(f)

        is_restored = output.is_file(restored_file)
        is_checksum_ok = check_stat and check_stat.get('state') == 'OK'

        def log_restore_status(message, script_exit):
            self.cfg.logger.info(message)
            self.script_exit = script_exit

        renew_message = f"If you want to restore from a new snapshot, delete the  '{restored_file}' file and start again."
        if is_restored and is_checksum_ok:
            log_restore_status(
                f"[RESTORE PASS] Already restored. is_restored={is_restored}, is_checksum_ok={is_checksum_ok}, {renew_message}.",
                True
            )
        elif is_restored:
            message = f"[RESTORE PASS] Already restored. is_restored={is_restored}, is_checksum_ok={is_checksum_ok}, {renew_message}"
            if check_stat is None:
                message += f" No '{checksum_result_file}' file found, but restore will be skipped."
            log_restore_status(message, True)
        elif is_checksum_ok:
            log_restore_status(
                f"[RESTORE PASS] No '{restored_file}' file found. CHECKSUM RESULT CHECK is 'OK'.",
                True
            )
        else:
            log_restore_status(
                f"[RESTORE][Start] The Restore DB Download (Not found file -> {restored_file}, {checksum_result_file})",
                False
            )

        return self.script_exit


    def check_downloaded_file(self):
        self.checksum_result = {}
        if output.is_file(self.log_files['download_error']):
            with open(self.log_files['download_error'], 'r') as file:
                contents = file.read().strip()
                if contents:
                    self.cfg.logger.error(f"[RESTORE] [ERROR] download_error.log\n\nE|{contents}\n")

        self.cfg.logger.info(
            f'[RESTORE] Base_dir = {self.db_path}, '
            f'checksum_filename = {self.stored_local_path["checksum_url"]}, '
            f'index_filename={self.stored_local_path["index_url"]}'
        )

        self.checksum_result = FileIndexer(
            base_dir=self.db_path,
            checksum_filename=self.stored_local_path['checksum_url'],
            index_filename=self.stored_local_path['index_url'],
            debug=self.debug,
            check_method="hash",
            prefix="").check()

        if self.checksum_result.get('status') == "OK":
            self.cfg.logger.info(f"[RESTORE] Completed checksum of downloaded file. "
                                 f"status={self.checksum_result['status']}")
        else:
            if self.checksum_result.get("status") == "FAIL":
                for file, result in self.checksum_result.get('error').items():
                    if file != 'date':
                        # url, output_path = self.get_file_url_info(file.replace("/data/", " ").split(' ')[-1])
                        # # result['url'] = url
                        # result['out'] = output_path
                        self.cfg.logger.error(f"[RESTORE][ERROR] {file}, {result}")
                        self.fail_result[file] = result
                if len(self.fail_result) > 0:
                    self.fail_result['date'] = self.checksum_result.get('error').get('date')
                    self.fail_result['state'] = False
                    # self.update_retry_count(False)
                else:
                    self.update_retry_count(True)

        self.create_checksum_result(status=self.checksum_result.get('status'))

    def get_file_url_info(self, file_name: str = ""):
        """
        > The function takes in a file name and returns the download url and output path of the file

        :param file_name: The name of the file you want to download
        :return: the file_download_url and file_output_path.
        """
        file_download_url = None
        file_output_path = None

        if file_name.split('/')[0] == 'data':
            file_name = file_name.split('/')[-1]

        with open(self.stored_local_path['index_url'], 'r') as f:
            for line_text in f.readlines():
                reg_url_pattern = re.compile(f'(https|http).*{file_name}\?version=([0-9][0-9][0-9][0-9])')
                if reg_url_pattern.match(line_text):
                    file_download_url = f'{line_text.strip()}'

                reg_output_pattern = re.compile(f'(\t)out=.*{file_name}')
                if reg_output_pattern.match(line_text):
                    file_output_path = f'{line_text.strip()}'

                if file_download_url and file_output_path:
                    break
        return file_download_url, file_output_path

    def create_checksum_result(self, status: str = "OK"):
        """
        It creates a JSON file with the name of the restored checksum marks file,
        and writes the status of the restored checksum marks file to it

        :param status: OK or FAIL, defaults to OK (optional)
        """
        if status == "OK":
            self.fail_result.clear()
            self.fail_result['state'] = "OK"

        with open(self.stored_local_path['restored_checksum_marks'], 'w') as f_json:
            json.dump(self.fail_result, f_json)

    def create_db_redownload_list(self):
        """
        It reads a json file, and if the value of a key is a dictionary,
        it writes the key and the value of the dictionary to a text file
        """
        self.retry_file_count = 0
        if output.is_file(self.stored_local_path['restored_checksum_marks']):
            with open(self.stored_local_path['restored_checksum_marks'], 'r') as f_json:
                self.checksum_value = json.load(f_json)

        for file, value in self.checksum_value.items():
            # print(file,value)
            if isinstance(value, dict):
                with open(self.stored_local_path['re_download_list'], 'a') as f:
                    self.retry_file_count += 1
                    f.write(f"{value.get('url')}\n")
                    f.write(f"\t{value.get('out')}\n")

        _re_download_list = self.stored_local_path['re_download_list']

        if output.is_file(_re_download_list):
            self.cfg.logger.info(f"'{_re_download_list}' has been successfully created.  size={get_size(_re_download_list)}, file_count={self.retry_file_count}")

    def fail_file_delete(self):
        """
        It reads a json file, and deletes all the files listed in the json file
        """
        with open(self.stored_local_path['restored_checksum_marks']) as f:
            fail_check_file_list = json.load(f)

        for del_file, value in fail_check_file_list.items():
            # print(del_file)
            if del_file != "date" and del_file != "state":
                if output.is_file(del_file):
                    os.remove(del_file)

    @staticmethod
    def _get_file_from_url(url: str = ""):
        file_name = url.split('/')[-1]
        file_name = file_name.split('?')[0]
        return file_name

    def _get_file_locate(self, url: str = ""):
        full_path = None
        if url:
            file_name = self._get_file_from_url(url)
            full_path = f"{self.restore_path}/{file_name}"
        return full_path

    def download_write_file(self, url: str = "", path: str = ""):
        """
        It downloads a file from a URL and writes it to a file

        :param url: The URL to download the file from
        :param path: The path to the directory where the file will be saved. If no path is specified, the file will be saved
        in the current directory
        :return: The full path and filename of the file that was downloaded.
        """
        if url:
            local_filename = self._get_file_from_url(url)
            if path:
                full_path_filename = f"{path}/{local_filename}"
            else:
                full_path_filename = local_filename

            with requests.get(url) as r:
                r.raise_for_status()
                self.cfg.logger.info(f"[RESTORE] {output.write_file(filename=full_path_filename, data=r.text)}")
        else:
            self.cfg.logger.error(f'[RESTORE] [ERROR] download_write_file() Invalid url {url}')
            raise Exception(f"[RESTORE] [ERROR] download_write_file() Invalid url {url}")

        return full_path_filename

    def download(self, redownload: bool = False):
        cmd = None
        command_result = {}
        run_start_time = default_timer()
        _default_cmd_opt = f" --allow-overwrite --log-level=error --log {self.log_files['download_error']}"
        if self.download_option:
            cmd_opt = f"{self.download_option} {_default_cmd_opt}"
        else:
            cmd_opt = f'-V -j10 -x8 --http-accept-gzip --disk-cache=64M -c ' \
                      f'{_default_cmd_opt}'

        self.cfg.logger.info(f"[RESTORE] Command option : '{cmd_opt}'")

        if self.download_url_type == "indexing":
            total_file_count = len(output.open_json(self.stored_local_path['checksum_url']))

            # add by hnsong 2022.08.25
            if redownload:
                self.cfg.logger.info(f"[RESTORE][RE-DOWNLOAD] DOWNLOAD TYPE = {self.download_url_type}, "
                                     f"RE-DOWNLOAD file list -> {self.stored_local_path['re_download_list']}")
                self.fail_file_delete()
                cmd = f"aria2c -i {self.stored_local_path['re_download_list']} -d {self.db_path} {cmd_opt}"
            else:
                self.cfg.logger.info(f"[RESTORE] DOWNLOAD TOTAL_FILE_COUNT = {total_file_count}")
                cmd = f"aria2c -i {self.stored_local_path['index_url']} -d {self.db_path} {cmd_opt}"

            command_result = base.run_execute(
                cmd=cmd,
                capture_output=False,
                hook_function=base.write_logging,
                log_filename=f"{self.log_files['download']}",
                total_file_count=total_file_count
            )

        elif self.download_url_type == "file_list":
            get_index_file = f'{self.download_url}/{self.network}/file_list.txt'
            self.file_download(get_index_file, self.restore_path, hash_value="skip")
            self.cfg.logger.info(f"[aria] Get index file, download_url_type = {self.download_url_type}, "
                                 f"url = {get_index_file}")

            cmd = f"aria2c -i {self.restore_path}/{get_index_file.split('/')[-1]} -d {self.db_path} {cmd_opt}"
            command_result = base.run_execute(cmd, capture_output=False, hook_function=base.write_logging,
                                              log_filename=f"{self.log_files['download']}")

        elif self.download_url_type:
            # S3 또는 Cloudfront URL check
            self.download_url_type_check()

            last_latency_rst = self.find_fastest_region()
            self.s3_bkurl = last_latency_rst.replace('/route_check', '')
            self.cfg.logger.info(f"S3 bucket url={self.s3_bkurl}, last_latency_rst={last_latency_rst}")

            index_download_url = f'{self.s3_bkurl}/{self.network}/index.txt'
            self.cfg.logger.info(f"[RESTORE] Get index file / download_url_type = {self.download_url_type}, "
                                 f"url = {index_download_url}")
            self.dl_dict, self.url_addr = self.get_file_list(index_download_url)

            # CID & Disk free size check & as_Download BackupFile Delete
            self.run_prejob(self.dl_dict)

            # Backup file download
            self.get_bkfile(self.url_addr, self.dl_dict)
            self.db_file_decompress()

        if cmd and command_result.get("stderr"):
            err_msg = f"[RESTORE] [ERROR] Error occurred downloading backup DB" \
                      f"\n cmd: '{cmd}'," \
                      f"\n stderr: {command_result.get('stderr')}"
            self.cfg.logger.error(err_msg)
            raise Exception(err_msg)

        run_elapsed = default_timer() - run_start_time
        elapsed_time = "{:5.3f}".format(run_elapsed)
        completed_msg = f"[RESTORE] Completed downloading. " \
                        f"elapsed_time={elapsed_time}s, {converter.format_seconds_to_hhmmss(run_elapsed)}"
        self.cfg.logger.info(completed_msg)
        try:
            if self.config.get('SLACK_WH_URL', None):
                output.send_slack(
                    url=self.config['SLACK_WH_URL'],
                    msg_text=Restore.result_formatter(completed_msg),
                    title='Restore',
                    msg_level='info'
                )
        except Exception as e:
            self.cfg.logger.error(f"[RESTORE] [ERROR] send_slack {e}")

    @staticmethod
    def result_formatter(log: str):
        return_str = f"[{datetime.today().strftime('%Y-%m-%d %H:%M:%S')}] {log}"
        return return_str

    def send_slack(self, msg_text=None, msg_level="info"):
        if self.is_send and msg_text:
            output.send_slack(url=self.send_url, msg_text=msg_text, msg_level=msg_level)

    def create_directory(self, dir_name: str = ""):
        try:
            if not os.path.exists(dir_name):
                os.makedirs(dir_name)
                self.cfg.logger.info(f"[RESTORE] Create a restore directory : {dir_name}")
        except OSError:
            self.cfg.logger.error(f"[RESTORE] [ERROR] Creating directory fail : {dir_name}")
            raise OSError(f"[RESTORE] [ERROR] Creating directory fail : {dir_name}")

    def download_url_type_check(self):
        if self.download_url_type == 's3' or self.download_url_type is None:
            # region code 치환을 위한 "_regioncode" add
            self.dl_url = f'https://{self.bucket_name_prefix}_regioncode.amazonaws.com'
            self.region_info = region_s3_info
            self.match_keyword = f'^MainNet'
        elif self.download_url_type == 'cf' or self.download_url_type == 'cloudfront':
            self.dl_url = f'https://{self.download_url}/_regioncode'
            self.region_info = region_cf_info
            self.match_keyword = f'^kr/.*MainNet'

    # s3 response time check
    def get_connect_time(self, url: str = "", name: str = "NULL"):
        status_code = 999
        try:
            response = requests.get(f'{url}', timeout=5)
            response_text = response.text
            elapsed_time = response.elapsed.total_seconds()
            status_code = response.status_code
        except Exception as e:
            elapsed_time = None
            response_text = None
            self.cfg.logger.error(f'[RESTORE] [ERROR] get_connect_time error : {url} -> {sys.exc_info()[0]} / {e}')
        return {"url": url, "time": elapsed_time, "name": name, "text": response_text, "status": status_code}

    # Check fast aws region
    def find_fastest_region(self):
        # worker Thread Setting
        worker_thread_cnt = 8
        pool = ThreadPool(worker_thread_cnt)

        results = {}
        i = 0

        spinner = Halo(text=f"Finding fastest region", spinner='dots')
        spinner.start()

        check_file = 'route_check'

        for region_name, region_code in self.region_info.items():
            dl_addr = re.sub('_regioncode', region_code, self.dl_url)  # region code 치환
            url = f'{dl_addr}' + f'/{check_file}'
            # exec_func = "get_connect_time"
            exec_args = (f"{url}", f"name={region_name}")
            results[i] = {}
            results[i]["data"] = pool.apply_async(self.get_connect_time, args=exec_args)
            i += 1
        pool.close()
        pool.join()

        last_latency = {}
        for i, p in results.items():
            data = p['data'].get()
            # print(f"data => {data}") if self.verbose else False
            if time is not None:
                if len(last_latency) == 0:
                    last_latency = data
                if last_latency.get("time") and data.get("time"):
                    if last_latency.get("time", 99999) >= data.get("time"):
                        last_latency = data
            # print(data) if self.verbose else False
        spinner.succeed(f'++ {line_info()} | [Done] Finding fastest region')
        return last_latency["url"]

    # get download backup file list
    def get_file_list(self, file_url: str = ""):
        self.cfg.logger.info(f"[RESTORE] get_file_list | file_url={file_url}")
        file_list_url = None
        try:
            res = requests.get(file_url)
            filelist_text = []
            temp_list = res.text.strip().split('\n')  # 마지막 라인이 공백일 경우 제거
            # print(temp_list)

            for file_list in temp_list:
                if re.match(self.match_keyword, file_list):
                    filelist_text.append(file_list)
            self.dl_url = re.sub('/[\w]+/bk', '', file_url).replace(f'/{self.network}/index.txt', '')
            file_list_url = f'{self.dl_url}/{filelist_text[-1]}'
            self.cfg.logger.info(f"[RESTORE] file_list_url={file_list_url}")
        except Exception as e:
            self.cfg.logger.error(f'[RESTORE] [ERROR] {e}')

        try:
            dl_file_list = requests.get(file_list_url)
            self.f_dict = dl_file_list.json()
        except Exception as e:
            self.cfg.logger.error(f'[RESTORE] [ERROR] {e}')

        return self.f_dict, self.dl_url

    def get_directory_usage_ratio(self, path: str = ""):
        total, used, free = shutil.disk_usage(path)
        dir_size = self.get_dir_size(path)
        # 남은 공간 대비 db 디렉토리 사용량 (퍼센트)
        dir_usage = dir_size / free * 100.0
        return dir_usage

    def get_dir_size(self, path: str = ""):
        total = 0
        with os.scandir(path) as paths:
            for entry in paths:
                if entry.is_file():
                    total += entry.stat().st_size
                elif entry.is_dir():
                    total += self.get_dir_size(entry.path)
        return total

    def run_prejob(self, dl_info):
        # chain id check
        if 'CID' in dl_info:
            chain_id = dl_info['CID']
            del_dir_list = ['contract', 'db', 'wal', 'genesis.zip']
            for del_item in del_dir_list:
                del_list = os.path.join(self.db_path, chain_id, del_item)
                self.cfg.logger.info(f"[RESTORE] Delete file is {del_list}")
                self.as_file_remove(del_list, file_opt=False)
            del dl_info['CID']

        # free disk size check
        if 'Total_size' in dl_info:
            total, used, p_free = shutil.disk_usage(self.db_path)
            dl_total_size = dl_info['Total_size'].split(' ')[0]
            if float(dl_total_size) * 1.5 < float(p_free):
                self.cfg.logger.info(f"[RESTORE] You have enough disk space ")
                del dl_info['Total_size']
            else:
                raise ValueError(f"[RESTORE] [ERROR] .{line_info()} | Not enough disk "
                                 f"- Download size : {dl_total_size} Byte , Disk Free Size : {p_free} Byte")
        else:
            directory_usage_ratio = self.get_directory_usage_ratio(self.db_path)
            # dir size free size check
            if directory_usage_ratio > self.used_disk_max_percent:
                self.send_slack(f"[RESTORE] [ERROR] Not enough disk space : {directory_usage_ratio:.2f}", "error")
                raise ValueError(f"[RESTORE] [ERROR] Not enough disk : {directory_usage_ratio:.2f}")
            else:
                self.cfg.logger.info(f"[RESTORE] You have enough disk space : {directory_usage_ratio:.2f} % ")

        # Download force delete ( Old Backup File Delete)
        if self.download_force:
            dl_path = os.path.join(self.db_path, self.download_path)
            del_list = os.listdir(dl_path)
            for del_file in del_list:
                if f'tar.zst' in del_file:
                    self.cfg.logger.info(f'[RESTORE] Delete Old Backup file  : {os.path.join(dl_path, del_file)}')
                    os.remove(os.path.join(dl_path, del_file))

    def get_bkfile(self, get_url: str = "", dl_info: dict = {}):
        # backup file download
        for f_url, cksum_value in dl_info.items():
            download_url = f'{get_url}/{f_url}'
            # Thread on
            t = threading.Thread(
                target=self.file_download,
                args=(
                    download_url,
                    os.path.join(self.db_path, self.restore_path),
                    cksum_value
                )
            )
            t.start()

        self.cfg.logger.info(f"[RESTORE] Download job wait ....")

        main_thread = threading.currentThread()
        for thread in threading.enumerate():
            log_print(f'{thread}', 'red')
            if thread is not main_thread:
                thread.join()
        self.cfg.logger.info(f"[RESTORE] Download job finished")

    def file_download(self, download_url, download_path, hash_value=None):
        self.cfg.logger.info(f"[RESTORE] download_url = {download_url}, "
                             f"download_path = {download_path}, hash_value = {hash_value}")
        try:
            diff_rst = None
            local_dl_file = os.path.join(download_path, download_url.split("/")[-1])
            # Old Download file Delete check
            if self.download_force or hash_value is "skip":
                if os.path.isfile(local_dl_file):
                    self.cfg.logger.info(f'[RESTORE] delete file => {local_dl_file}')
                    os.remove(local_dl_file)

            if os.path.isfile(local_dl_file):
                if hash_value is not "skip":
                    diff_rst = Restore.download_diff(local_dl_file, hash_value)
                    if diff_rst == 'nok':
                        os.remove(local_dl_file)
                        self.cfg.logger.info(
                            f'[RESTORE] {threading.get_ident()}, download_url={download_url.split("/")[-1]}, '
                            f'diff_rst={diff_rst}, delete={local_dl_file}'
                        )
                        diff_rst = None

            if diff_rst is None:
                start_time = default_timer()
                download_cmd = None

                if self.download_tool == 'axel' or self.download_tool is None:
                    # axel_option = f"-k -n {cpu_count} --verbose"    ###  axel 2.4 버전에서는 -k 옵션이 제외됨.
                    axel_option = f"-n {self.cpu_count} --verbose"
                    download_cmd = f'axel {axel_option} {download_url} -o "{download_path}"'
                elif self.download_tool == 'aria2' or self.download_tool == 'aria2c':
                    aria2_option = f'-j {self.cpu_count}'
                    download_cmd = f'aria2c {aria2_option} {download_url} -d {download_path}'

                if download_cmd:
                    run_stat = base.run_execute(download_cmd, capture_output=True)
                    print(run_stat)

                elapsed = default_timer() - start_time
                time_completed_at = "{:5.3f}s".format(elapsed)

                if hash_value is not "skip":
                    diff_rst = Restore.download_diff(local_dl_file, hash_value)
                    if diff_rst == 'ok':
                        self.cfg.logger.info(
                            f'[RESTORE] {threading.get_ident()}, {download_url.split("/")[-1]}, {diff_rst}, '
                            f'time_completed_at = {time_completed_at}'
                        )
                    else:
                        err_msg = f"[RESTORE] [ERROR] Download file Checksum Check Fail - '{local_dl_file}'"
                        self.cfg.logger.error(err_msg)
                        raise ValueError(err_msg)
            else:
                self.cfg.logger.info(
                    f'[RESTORE] {threading.get_ident()}, {download_url.split("/")[-1]}, exist file (checksum is Same)'
                )

        except Exception as e:
            self.cfg.logger.error(f'[RESTORE] [ERROR] {e}')
            # log_print(f"-- {line_info()} | {e}","red")

    # Old file remove
    def as_file_remove(self, delete_path, file_opt=False):
        # /app/goloop/data/{CID} , ## /app/goloop/data/[restore]/*.tar*
        delete_dir = os.path.join(delete_path)
        self.cfg.logger.info(f'[RESTORE] Delete a job dir : {delete_dir}')

        try:
            if file_opt:
                # Delete directory file
                filelist = os.listdir(f"{delete_dir}")
                for item in filelist:
                    if f".tar.zst" in item:
                        os.remove(os.path.join(delete_dir, item))
                        self.cfg.logger.info(f"[RESTORE] delete : {delete_dir} {item}")
            else:
                p_rst = f'deleted : {delete_dir}"'
                # Delete directory
                if os.path.isdir(delete_dir):
                    shutil.rmtree(delete_dir)
                elif os.path.isfile(delete_dir):
                    os.remove(os.path.join(delete_dir))
                else:
                    p_rst = f'Not found {delete_dir}'
                self.cfg.logger.info(f"[RESTORE] {p_rst}")

        except OSError:
            self.cfg.logger.error(f'[RESTORE] [ERROR] file_remove ({file_opt}), RESTORE stop!')
            raise OSError(f"[RESTORE] [ERROR] file_remove ({file_opt})")

    # S3에 업로드된 파일과 다운로드 된 파일 의 MD5 체크섬 비교
    @staticmethod
    def download_diff(download_file, orig_hash):
        localfile_hash = Restore.get_hash(download_file)
        if localfile_hash == orig_hash:
            hash_rst = "ok"
        else:
            hash_rst = "nok"
        return hash_rst

    # MD5 HASH
    @staticmethod
    def get_hash(path, blocksize=65536):
        """
        It reads the file in chunks of 65536 bytes, and then updates the hash with each chunk

        :param path: The path to the file you want to hash
        :param blocksize: The size of the chunk of data to read from the file at a time, defaults to 65536 (optional)
        :return: The md5 hash of the file.
        """
        afile = open(path, 'rb')
        hasher = hashlib.md5()
        buf = afile.read(blocksize)
        while len(buf) > 0:
            hasher.update(buf)
            buf = afile.read(blocksize)
        afile.close()
        return hasher.hexdigest()

    def db_file_decompress(self):
        self.cfg.logger.info(f'[RESTORE] decompress start')
        comp_algorithm = 'pzstd'
        old_run_path = os.getcwd()

        if os.path.isdir(self.db_path):
            os.chdir(self.db_path)
            self.cfg.logger.info(f'[RESTORE] Change job directory is \"{self.db_path}\"')
            sour_dir = os.path.join(self.db_path, self.restore_path)
            cmd = f"cat {sour_dir}/*tar.* | {comp_algorithm} -cd | tar -xf - -C {self.db_path}"

            self.cfg.logger.info(f'[RESTORE] Decompress Command = {cmd}')

            if base.run_execute(cmd).get("stderr"):
                self.cfg.logger.error(f'[RESTORE] [ERROR] Failed Decompression - "{cmd}", RESTORE Stop!')
                raise OSError(f"[RESTORE] [ERROR] Failed Decompression - '{cmd}'")
        else:
            self.cfg.logger.error(f'[RESTORE] [ERROR] Can not found directory = {self.db_path}')

        # 이전 디렉토리로  변경
        os.chdir(old_run_path)


# It's a class that takes a filename and a size, and then prints out the percentage of the file that has been uploaded
class ProgressPercentage(object):
    def __init__(self, filename):
        self._filename = filename
        self._size = float(os.path.getsize(filename))
        self._seen_so_far = 0
        self._lock = threading.Lock()
        self._prevent_bytes = 0

    def __call__(self, bytes_amount):
        """
        It takes the amount of bytes downloaded, adds it to the amount of bytes downloaded so far, calculates the percentage
        of the file downloaded, and prints it to the screen

        :param bytes_amount: The number of bytes transferred so far
        """
        # To simplify we'll assume this is hooked up
        # to a single filename.
        with self._lock:
            self._seen_so_far += bytes_amount
            percentage = (self._seen_so_far / self._size) * 100
            # tx = bytes_amount - self._prevent_bytes
            sys.stdout.write(
                "\r \t %s  %s / %s  (%.2f%%) " % (
                    self._filename, converter.convert_bytes(
                        self._seen_so_far), converter.convert_bytes(self._size),
                    percentage))
            sys.stdout.flush


def main():
    # 상위 모듈 import 하기 위한 경로 추가(?)
    # parent_dir = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
    # sys.path.append(parent_dir)
    # sys.path.append(parent_dir+"/..")

    from config.configure import Configure

    # test config  json download url  : https://d1hfk7wpm6ar6j.cloudfront.net/SejongNet/default_configure.json
    # # test path & file   : /goloop/default_configure.json
    use_file = False
    cfg = Configure(use_file=use_file)
    config = cfg.config
    '''
    +  /goloop/configure.yaml  파일 내 참고 dict value
    settings
       > env
          > COMPOSE_ENV
              -  "SERVICE": "MainNet",
              -  "BASE_DIR": "/goloop",
              -  "DOWNLOAD_FORCE": "true",
              -  "RESTORE_PATH": "restore",
              -  "DOWNLOAD_TOOL" : "aria2c",
              -  "DOWNLOAD_URL_TYPE" : "file_list",
              -  "DOWNLOAD_URL" : "https://download.solidwallet.io"
    
    setting 
       > icon2
           - "GOLOOP_NODE_DIR" : "/goloop/data"
    '''
    icon2_config = config

    # Goloop DB PATH
    if icon2_config.get('GOLOOP_NODE_DIR'):
        db_path = icon2_config['GOLOOP_NODE_DIR']
    else:
        default_db_path = 'data'
        # base_dir = compose_env_config['BASE_DIR']
        base_dir = icon2_config['BASE_DIR']
        db_path = os.path.join(base_dir, default_db_path)

    network = icon2_config['SERVICE']
    restore_path = icon2_config['RESTORE_PATH']
    dl_force = icon2_config['DOWNLOAD_FORCE']
    download_tool = icon2_config['DOWNLOAD_TOOL']
    download_url = icon2_config['DOWNLOAD_URL']
    download_url_type = icon2_config['DOWNLOAD_URL_TYPE']

    Restore(
        db_path=db_path,
        network=network,
        download_path=restore_path,
        download_force=dl_force,
        download_url=download_url,
        download_tool=download_tool,
        download_url_type=download_url_type
    ).run()


if __name__ == '__main__':
    main()
