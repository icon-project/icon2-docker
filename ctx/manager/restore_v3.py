#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import threading
import sys, os
import time
import shutil, hashlib
import inspect
import re
import requests
from datetime import datetime
from multiprocessing.pool import ThreadPool
from halo import Halo
from timeit import default_timer

from common import converter, output, base
from common.converter import region_info as region_s3_info  ### regeion config
from common.converter import region_cf_info, todaydate  ### regeion config

from config.configure import Configure as CFG

from .file_indexing import FileIndexer

# sys.excepthook = output.exception_handler

## SSL Warnning
base.disable_ssl_warnings()

filename = __file__
get_filename = filename.split('/')[-1]


def line_info(return_type=None):
    """
       common/output.py 안에 추가 할 예정
       추가 할 경우  import 필요
       from common.output import line_info
       - line number 및 function 위치를 출력하기 위함
    """
    # line number
    cf = inspect.currentframe()
    linenumber = cf.f_back.f_lineno

    # Call to Function name
    func_name = cf.f_back.f_code.co_name

    # file name
    frame = inspect.stack()[1]
    module = inspect.getmodule(frame[0])

    if return_type == 'filename':
        result_info = f'{get_filename}'
    elif return_type == 'function' or return_type == 'func_name' or return_type == 'f_name':
        result_info = f'{func_name}'
    elif return_type == 'lineinfo' or return_type == 'linenum' or return_type == 'lineno':
        result_info = f'{linenumber}'
    elif return_type == 'info_all' or return_type is None:
        result_info = f'{get_filename}({func_name}.{linenumber})'
    else:
        result_info = f'{get_filename}({func_name}.{linenumber})'

    return result_info


def log_print(msg, color=None, level=None):
    """
      log 및 print를 하기 위한 함수
    """
    color = color if color else f'green'
    level = level if level else f'INFO'

    now_time = (datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3])
    output.cprint(f'[{now_time}] [{level:5}] | {msg}', color)


class Restore:
    def __init__(self,
                 region="kr",  # 사용안함
                 db_path=None,  # .settings.icon2.GOLOOP_NODE_DIR
                 network="MainNet",  # .settings.env.SERVICE
                 send_url=None,  # 사용자 입력   /  없어도무방   .settings.env.RESTORE_SEND_URL
                 bucket_name_prefix="icon2-backup",  # 사용자 입력(docker 변수로 ) 없을 경우 defaut 사용  : false
                 download_type="multi",  # 변경 필요 없음
                 download_path='restore',  # Download directory | 사용자 입력(docker 변수로) 없을 경우 defaut 사용  : false
                 download_url='download.solidwallet.io',  # Downlaod type check  s3 or cloud front , Default : s3 download
                 download_url_type='s3',  # Downlaod type check  s3 or cloud front , Default : s3 download,cloudfront]" or "file_list"
                 download_tool='axel',  # Download Tool command option .  Default Axel command  [ axel | aria2(aria2c) ]
                 download_force=False,  # Download file이 동일할경우에 대한 액션 True일 경우 모두 삭제 후 download /
                 # False일 경우 동일 파일 비교 후 다를 경우 삭제 |  사용자 입력(docker 변수로 ) 없을 경우 default 사용  : false
                 ):
        """

        :param region: 사용안함
        :param db_path: .settings.icon2.GOLOOP_NODE_DIR
        :param network: .settings.env.SERVICE
        :param send_url: 사용자 입력 /없어도 무방   .settings.env.RESTORE_SEND_URL
        :param bucket_name_prefix: 사용자 입력(docker 변수로 ) 없을 경우 default 사용  : false
        :param download_type:  변경 필요 없음
        :param download_path: Download directory | 사용자 입력(docker 변수로) 없을 경우 defaut 사용  : false
        :param download_url: Downlaod type check  s3 or cloud front , Default : s3 download
        :param download_url_type: Downlaod type check  s3 or cloud front , Default : s3 download,cloudfront]" or "file_list"
        :param download_tool: Download Tool command option.  Default Axel command  [ axel | aria2(aria2c) ]
        :param download_force: Download file이 동일할경우에 대한 액션 True일 경우 모두 삭제 후 download
                               False일 경우 동일 파일 비교 후 다를 경우 삭제 |  사용자 입력(docker 변수로 ) 없을 경우 default 사용  : false
        """
        self.cfg = CFG()
        self.config = self.cfg.config
        # self.cfg.logger = self.cfg.logger

        self.dl_dict = {}
        self.url_addr = None
        self.s3_bkurl = None

        self.region = region  # 사용안함
        self.db_path = db_path  # 필수 Default => icon2 : /app/goloop
        self.network = network  # 필수  Blockchain  node network name
        self.bucket_name_prefix = bucket_name_prefix  # 필수

        self.download_path = download_path  # Change variable name restore_path to download_path
        self.download_filename = ""
        self.download_url_type = download_url_type
        self.download_type = download_type  # 사용안함
        self.download_force = download_force
        self.download_tool = download_tool  # Default axel
        self.verbose = None
        self.restore_path = None

        self.checksum_result = {}

        if self.download_url_type == "indexing":
            self.download_url = download_url
        elif self.download_url_type == "file_list":
            self.download_url = "https://icon2-backup-kr.s3.ap-northeast-2.amazonaws.com/s3sync"
        else:
            self.download_url = re.sub('(http|https)://', '', download_url)
        # Send url check
        self.send_url = send_url  # 없어도 무방
        if send_url:
            self.is_send = True
        else:
            self.is_send = False
        # Icon2 node DB Path check
        if self.db_path is None or not output.is_file(self.db_path):
            raise ValueError(f"-- {line_info()} | | db_path not found - '{self.db_path}'")

        self.cpu_count = os.cpu_count()
        self.used_disk_max_percent = 70

        self.env = self.cfg.config
        self.base_log_dir = f"{self.env['BASE_DIR']}/logs"
        if self.env.get('CC_DEBUG'):
            self.debug = self.env['CC_DEBUG']
        else:
            self.debug = False

        self._prepare()
        self.cfg.logger.info(f"[RESTORE] DOWNLOAD_URL={self.download_url}, "
                             f"SERVICE={self.network}, "
                             f"DOWNLOAD_URL_TYPE={self.download_url_type}, "
                             f"RESTORE_PATH={self.restore_path} ")

        output.write_file(self.stored_local_path['restored_marks'], todaydate('ms'))
        self.download()
        self.check_downloaded_file()

        if self.checksum_result and self.checksum_result.get("status") == "FAIL":
            self.cfg.logger.info("[RESTORE] Try the one more downloading")
            self.download()
            self.check_downloaded_file()

        if self.checksum_result.get("status") == "FAIL":
            raise Exception(f"File checksum error")

    def _prepare(self):
        self.restore_path = os.path.join(self.db_path, self.download_path)
        self.create_directory(self.restore_path)

        self.log_files = {
            "download": f"{self.base_log_dir}/download.log",
            "download_error": f"{self.base_log_dir}/download_error.log",
        }

        self.stored_local_path = {
            "index_url": "",
            "checksum_url": "",
            "restored_marks": f"{self.restore_path}/RESTORED"
        }

        if output.is_file(self.stored_local_path['restored_marks']):
            self.cfg.logger.info(
                f"[RESTORE PASS] Already restored. If you want to start over, delete the '{self.stored_local_path['restored_marks']}' file.")
            exit()
        for log_file in self.log_files.values():
            if output.is_file(log_file):
                self.cfg.logger.info(f"[RESTORE] Exists file {log_file}, Delete a old file")
                # for not to miss the file description
                output.write_file(log_file, " ")

        download_info_url = f"{self.download_url}/{self.network}.json"
        download_info_res = requests.get(download_info_url)
        if download_info_res.status_code == 200:
            download_info = download_info_res.json()
            self.cfg.logger.info(f"[RESTORE] index_url={download_info.get('index_url')}, checksum_url={download_info.get('checksum_url')}")
            for url_name in ["index_url", "checksum_url"]:
                # self.file_download(download_url=download_info.get(url_name), download_path=self.download_path, hash_value="skip")
                self.download_write_file(url=download_info.get(url_name), path=self.download_path)
                self.stored_local_path[url_name] = self._get_file_locate(download_info.get(url_name))
        else:
            self.cfg.logger.info(f'[RESTORE] Invalid url or service name, url={download_info_res}, status={download_info_res.status_code} ')

    def check_downloaded_file(self):
        self.checksum_result = {}
        with open(self.log_files['download_error'], 'r') as file:
            contents = file.read().strip()
            if contents:
                self.cfg.logger.error(f"[RESTORE] download_error.log\n\nE|{contents}\n")

        self.checksum_result = FileIndexer(
            base_dir=self.db_path,
            checksum_filename=self.stored_local_path['checksum_url'],
            debug=self.debug,
            check_method="hash",
            prefix="").check()

        if self.checksum_result.get('status') == "OK":
            self.cfg.logger.info(f"[RESTORE] Completed checksum of downloaded file. status={self.checksum_result['status']}")
        else:
            if self.checksum_result.get("status") == "FAIL":
                for file, result in self.checksum_result.items():
                    self.cfg.logger.error(f"[RESTORE][ERROR] {file}, {result}")
            # raise Exception(f"File checksum error")

    @staticmethod
    def _get_file_from_url(url):
        file_name = url.split('/')[-1]
        file_name = file_name.split('?')[0]
        return file_name

    def _get_file_locate(self, url):
        full_path = None
        if url:
            file_name = self._get_file_from_url(url)
            full_path = f"{self.download_path}/{file_name}"
        return full_path

    def download_write_file(self, url, path=None):
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
            raise Exception(f"download_write_file() Invalid url {url}")

        return full_path_filename

    def download(self):
        run_start_time = default_timer()
        cmd_opt = f'-V -j10 -x8 --http-accept-gzip --disk-cache=64M  ' \
                  f'-c --allow-overwrite --log-level=error --log {self.log_files["download_error"]}'

        cmd = None
        command_result = {}

        if self.download_url_type == "indexing":
            cmd = f"aria2c -i {self.stored_local_path['index_url']} -d {self.db_path} {cmd_opt}"
            total_file_count = len(output.open_json(self.stored_local_path['checksum_url']))
            self.cfg.logger.info(f"[RESTORE] total_file_count = {total_file_count}")

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
            self.cfg.logger.info(f"[aria] Get index file, download_url_type = {self.download_url_type}, url = {get_index_file}")
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
            self.cfg.logger.info(f"Get index file / download_url_type = {self.download_url_type}, url = {index_download_url}")
            self.dl_dict, self.url_addr = self.get_file_list(index_download_url)
            # CID & Disk free size check & as_Download BackupFile Delete
            self.run_prejob(self.dl_dict)
            # Backup file download
            self.get_bkfile(self.url_addr, self.dl_dict)
            self.db_file_decompress()

        if cmd and command_result.get("stderr"):
            raise Exception(f"Error occurred downloading backup DB \n cmd: '{cmd}', \n stderr: {command_result.get('stderr')}")

        run_elapsed = default_timer() - run_start_time
        elapsed_time = "{:5.3f}".format(run_elapsed)
        completed_msg = f"[RESTORE] Completed downloading. elapsed_time={elapsed_time}s, {converter.format_seconds_to_hhmmss(run_elapsed)}"
        self.cfg.logger.info(completed_msg)
        try:
            if self.config.get('SLACK_WH_URL', None):
                output.send_slack(
                    url=self.config['SLACK_WH_URL'],
                    msg_text=self.result_formatter(completed_msg),
                    title='Restore',
                    msg_level='error'
                )
        except Exception as e:
            self.cfg.logger.error(f"[ERROR] send_slack {e}")

    def result_formatter(self, log: str):
        return_str = f"[{datetime.today().strftime('%Y-%m-%d %H:%M:%S')}] {log}"
        return return_str

    def send_slack(self, msg_text=None, msg_level="info"):
        if self.is_send and msg_text:
            output.send_slack(url=self.send_url, msg_text=msg_text, msg_level=msg_level)

    def create_directory(self, dir_name):
        try:
            if not os.path.exists(dir_name):
                os.makedirs(dir_name)
                self.cfg.logger.info(f"[RESTORE] Create a restore directory : {dir_name}")
        except OSError:
            raise OSError(f"-- {line_info()} | Error: Creating directory fail. : {dir_name}")

    def download_url_type_check(self):
        if self.download_url_type == 's3' or self.download_url_type is None:
            self.dl_url = f'https://{self.bucket_name_prefix}_regioncode.amazonaws.com'
            self.region_info = region_s3_info
            self.match_keyword = f'^MainNet'
        elif self.download_url_type == 'cf' or self.download_url_type == 'cloudfront':
            self.dl_url = f'https://{self.download_url}/_regioncode'
            self.region_info = region_cf_info
            self.match_keyword = f'^kr/.*MainNet'

    # s3 response time check
    def get_connect_time(self, url, name="NULL"):
        status_code = 999
        try:
            response = requests.get(f'{url}', timeout=5)
            response_text = response.text
            elapsed_time = response.elapsed.total_seconds()
            status_code = response.status_code
        except Exception as e:
            elapsed_time = None
            response_text = None
            log_print(f"-- {line_info()} | get_connect_time error : {url} -> {sys.exc_info()[0]} / {e}", "red")
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
            dl_addr = re.sub('_regioncode', region_code, self.dl_url)  ## region code 치환
            URL = f'{dl_addr}' + f'/{check_file}'
            # exec_func = "get_connect_time"
            exec_args = (f"{URL}", f"name={region_name}")
            results[i] = {}
            results[i]["data"] = pool.apply_async(self.get_connect_time, args=exec_args)
            i += 1
        pool.close()
        pool.join()

        last_latency = {}
        for i, p in results.items():
            data = p['data'].get()
            print(f"data => {data}") if self.verbose else False
            if time is not None:
                if len(last_latency) == 0:
                    last_latency = data
                if last_latency.get("time") and data.get("time"):
                    if last_latency.get("time", 99999) >= data.get("time"):
                        last_latency = data
            print(data) if self.verbose else False
        spinner.succeed(f'++ {line_info()} | [Done] Finding fastest region')
        return last_latency["url"]

    # get download backup file list
    def get_file_list(self, file_url):
        self.cfg.logger.info(f"file_url={file_url}")
        file_list_url = None
        try:
            res = requests.get(file_url)
            filelist_text = []
            temp_list = res.text.strip().split('\n')  ### 마지막 라인이 공백일 경우 제거
            print(temp_list)

            for file_list in temp_list:
                if re.match(self.match_keyword, file_list):
                    filelist_text.append(file_list)
            self.dl_url = re.sub('/[\w]+/bk', '', file_url).replace(f'/{self.network}/index.txt', '')
            file_list_url = f'{self.dl_url}/{filelist_text[-1]}'
            self.cfg.logger.info(f"file_list_url={file_list_url}")

        except Exception as e:
            self.cfg.logger.error(e)
        try:
            # log_print(f"++ {line_info()} | {file_list_url}","green")
            dl_file_list = requests.get(file_list_url)
            self.f_dict = dl_file_list.json()
        except Exception as e:
            self.cfg.logger.error(e)
            # log_print(f"-- {line_info()} | {e}", "red")

        return self.f_dict, self.dl_url

    def dir_free_size(self, path):
        total, used, free = shutil.disk_usage(path)
        dirsize = self.get_dir_size(path)
        # 남은 공간 대비 db 디렉토리 사용량 (퍼센트)
        dirusage = dirsize / free * 100.0
        return dirusage

    def get_dir_size(self, path):
        total = 0
        with os.scandir(path) as it:
            for entry in it:
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
                self.as_file_remove(del_list, file_opt=False)
            del dl_info['CID']

        # free disk size check
        if 'Total_size' in dl_info:
            total, used, p_free = shutil.disk_usage(self.db_path)
            DL_Total_Size = dl_info['Total_size'].split(' ')[0]
            if float(DL_Total_Size) * 1.5 < float(p_free):
                self.cfg.logger.info(f"You have enough disk space ")
                del dl_info['Total_size']
            else:
                raise ValueError(f"++ {line_info()} | Not enough disk - Download size : {DL_Total_Size} Byte , Disk Free Size : {p_free} Byte")
        else:
            dir_usage = self.dir_free_size(self.db_path)
            # dir size free size check
            if dir_usage > self.used_disk_max_percent:
                self.send_slack(f"Not enough disk space : {dir_usage:.2f}", "error")
                raise ValueError(f"-- {line_info()} | Not enough disk : {dir_usage:.2f}")
            else:
                self.cfg.logger.info(f"You have enough disk space : {dir_usage:.2f} % ")

        # Download force delete ( Old Backup File Delete)
        if self.download_force:
            dl_path = os.path.join(self.db_path, self.download_path)
            del_list = os.listdir(dl_path)
            for del_file in del_list:
                if f'tar.zst' in del_file:
                    self.cfg.logger.info(f'Delete Old Backup file  : {os.path.join(dl_path, del_file)}')
                    os.remove(os.path.join(dl_path, del_file))

    def get_bkfile(self, get_url, dl_info):
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

        self.cfg.logger.info(f"Download job wait ....")

        main_thread = threading.currentThread()
        for thread in threading.enumerate():
            log_print(f'{thread}', 'red')
            if thread is not main_thread:
                thread.join()
        self.cfg.logger.info(f"Download job finished")

    def file_download(self, download_url, download_path, hash_value=None):
        self.cfg.logger.info(f"download_url = {download_url}, download_path = {download_path}, hash_value = {hash_value}")
        try:
            diff_rst = None
            local_dl_file = os.path.join(download_path, download_url.split("/")[-1])
            # Old Download file Delete check
            if self.download_force or hash_value is "skip":
                if os.path.isfile(local_dl_file):
                    self.cfg.logger.info(f'>>> delete => {local_dl_file}')
                    os.remove(local_dl_file)

            if os.path.isfile(local_dl_file):
                if hash_value is not "skip":
                    diff_rst = self.download_diff(local_dl_file, hash_value)
                    if diff_rst == 'nok':
                        os.remove(local_dl_file)
                        self.cfg.logger.info(
                            f'{threading.get_ident()}, download_url={download_url.split("/")[-1]}, diff_rst={diff_rst} , delete={local_dl_file}')
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

                elapsed = default_timer() - start_time
                time_completed_at = "{:5.3f}s".format(elapsed)

                if hash_value is not "skip":
                    diff_rst = self.download_diff(local_dl_file, hash_value)
                    if diff_rst == 'ok':
                        self.cfg.logger.info(
                            f'{threading.get_ident()}, {download_url.split("/")[-1]}, {diff_rst}, time_completed_at = {time_completed_at}'
                        )
                    else:
                        raise ValueError(f"++ {line_info()}, download file Checksum Check Fail - '{local_dl_file}'")
            else:
                self.cfg.logger.info(f'{threading.get_ident()}, {download_url.split("/")[-1]}, exist file (checksum is Same)')

        except Exception as e:
            self.cfg.logger.error(e)
            # log_print(f"-- {line_info()} | {e}","red")

    # Old file remove
    def as_file_remove(self, delete_path, file_opt=False):
        # /app/goloop/data/{CID} , ## /app/goloop/data/[restore]/*.tar*
        delete_dir = os.path.join(delete_path)
        self.cfg.logger.info(f'Delete a job dir : {delete_dir}')

        try:
            if file_opt:
                # Delete directory file
                filelist = os.listdir(f"{delete_dir}")
                for item in filelist:
                    if f".tar.zst" in item:
                        os.remove(os.path.join(delete_dir, item))
                        self.cfg.logger.info(f"-- {line_info()}| delete : {delete_dir} {item}")
            else:
                p_rst = f'deleted : {delete_dir}"'
                # Delete directory
                if os.path.isdir(delete_dir):
                    shutil.rmtree(delete_dir)
                elif os.path.isfile(delete_dir):
                    os.remove(os.path.join(delete_dir))
                else:
                    p_rst = f'Not found {delete_dir}'
                self.cfg.logger.info(f"{p_rst}")

        except OSError:
            raise OSError(f"-- {line_info()} | Error: file_remove ({file_opt})")

    # S3에 업로드된 파일과 다운로드 된 파일 의 MD5 체크섬 비교
    def download_diff(self, download_file, orig_hash):
        localfile_hash = self.getHash(download_file)
        if localfile_hash == orig_hash:
            hash_rst = "ok"
        else:
            hash_rst = "nok"
        return hash_rst

    # MD5 HASH
    def getHash(self, path, blocksize=65536):
        afile = open(path, 'rb')
        hasher = hashlib.md5()
        buf = afile.read(blocksize)
        while len(buf) > 0:
            hasher.update(buf)
            buf = afile.read(blocksize)
        afile.close()
        return hasher.hexdigest()

    def db_file_decompress(self):
        self.cfg.logger.info(f'decompress start')
        comp_algorithm = 'pzstd'
        old_run_path = os.getcwd()

        if os.path.isdir(self.db_path):
            os.chdir(self.db_path)
            self.cfg.logger.info(f'Change job directory is \"{self.db_path}\"')
            sour_dir = os.path.join(self.db_path, self.restore_path)
            cmd = f"cat {sour_dir}/*tar.* | {comp_algorithm} -cd | tar -xf - -C {self.db_path}"

            self.cfg.logger.info(f'cmd = {cmd}')

            if base.run_execute(cmd).get("stderr"):
                raise OSError(f"Failed Decompression - '{cmd}'")
        else:
            self.cfg.logger.error(f'Can not found directory = {self.db_path}')
        # 이전  디렉토리로  변경
        os.chdir(old_run_path)


class ProgressPercentage(object):
    def __init__(self, filename):
        self._filename = filename
        self._size = float(os.path.getsize(filename))
        self._seen_so_far = 0
        self._lock = threading.Lock()
        self._prevent_bytes = 0

    def __call__(self, bytes_amount):
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

    from config.configure import Configure as CFG

    # test config  json download url  : https://d1hfk7wpm6ar6j.cloudfront.net/SejongNet/default_configure.json
    ###  test path & file   : /goloop/default_configure.json
    # use_file=True
    use_file = False
    cfg = CFG(use_file=use_file)
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

    # Restore Options
    # network  =  MainNet | SejongNet ....
    # network = env_config['SERVICE'] if env_config.get('SERVICE') else compose_env_config['SERVICE']
    # restore_path = env_config['RESTORE_PATH'] if env_config.get('RESTORE_PATH') else compose_env_config['RESTORE_PATH']
    # dl_force = env_config['DOWNLOAD_FORCE'] if env_config.get('DOWNLOAD_FORCE') else compose_env_config['DOWNLOAD_FORCE']
    # download_tool = env_config['DOWNLOAD_TOOL'] if env_config.get('DOWNLOAD_TOOL') else compose_env_config['DOWNLOAD_TOOL']
    # download_url = env_config['DOWNLOAD_URL'] if env_config.get('DOWNLOAD_URL') else compose_env_config['DOWNLOAD_URL']
    # download_url_type = env_config['DOWNLOAD_URL_TYPE'] if env_config.get('DOWNLOAD_URL_TYPE') else compose_env_config['DOWNLOAD_URL_TYPE']
    network = icon2_config['SERVICE']
    restore_path = icon2_config['RESTORE_PATH']
    dl_force = icon2_config['DOWNLOAD_FORCE']
    download_tool = icon2_config['DOWNLOAD_TOOL']
    download_url = icon2_config['DOWNLOAD_URL']
    download_url_type = icon2_config['DOWNLOAD_URL_TYPE']

    ## Test path
    # db_path = "/app/goloop/data2"
    ## Test config
    # network = "MainNet"
    # restore_path = "restore"
    # dl_force = True
    # download_url = f'https://icon2-backup-kr.s3.ap-northeast-2.amazonaws.com/s3sync'    ##s3sync url
    # download_url = f'https://download.solidwallet.io'            ## test cf
    # download_tool = "aria2"
    # download_url_type = "cf"

    # print(f'db_path = {db_path}')
    # print(f'network = {network}')
    # print(f'restore_path = {restore_path}')

    # print(f'dl_force = {dl_force}')
    # print(f'download_tool = {download_tool}')
    # print(f'download_url = {download_url}')
    # print(f'download_url_type = {download_url_type}')

    Restore(
        db_path=db_path,
        network=network,
        download_path=restore_path,
        download_force=dl_force,
        download_url=download_url,
        download_tool=download_tool,
        download_url_type=download_url_type
    )


if __name__ == '__main__':
    main()
