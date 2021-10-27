#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import threading
import boto3
import logging
import sys, os, time, datetime , inspect
import shutil, hashlib
import argparse
import requests
from termcolor import colored, cprint
from multiprocessing.pool import ThreadPool
from halo import Halo
from boto3.s3.transfer import TransferConfig
from botocore.handlers import disable_signing
from timeit import default_timer
from inspect  import  currentframe

parent_dir = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
sys.path.append(parent_dir)
sys.path.append(parent_dir+"/..")
from common import converter, output, base
from common.converter import region_info     ### regeion config
from common.output import lineno, script_name, funcname

sys.excepthook = output.exception_handler

class Restore:
    def __init__(
        self,
        core_version="core2",
        db_path=None,
        network="MainNet",
        send_url=None,
        bucket_name_prefix="icon2-backup",
        region="kr",
        download_type="multi",
        restore_path='restore',   ### Download directory
        ):

        self.core_version = core_version
        self.db_path = db_path
        self.network = network
        self.send_url = send_url
        self.bucket_name_prefix = bucket_name_prefix
        self.region = region
        self.download_type = download_type
        self.restore_path = restore_path

        self.download_filename = ""
        self.verbose = None

        if send_url:
            self.is_send = True
        else:
            self.is_send = False

        if self.db_path is None or not output.is_file(self.db_path):
            raise ValueError(f"{script_name()}({funcname()}.{lineno()}) | db_path not found - '{self.db_path}'")

        self.get_nproc = ''.join(base.run_execute('nproc', capture_output=True)['stdout'])

        self.run()

    ####  class main run function
    def run(self):

        run_start_time = default_timer()
        diskcheck_per = 70

        # Restore WorkDir Create
        self.createFolder(os.path.join(self.db_path, self.restore_path))

        ## fastest region check
        last_latency = self.find_fastest_region()
        cprint(f'{script_name()}({funcname()}.{lineno()}) | {last_latency["url"]}', 'grey')

        self.s3_bkurl = last_latency['url'].replace('/route_check','')
        cprint(f'{script_name()}({funcname()}.{lineno()}) | {self.s3_bkurl}', 'grey')

	## get index.txt
        index_download_url = f'{self.s3_bkurl}/{self.network}/index.txt'
        cprint(f'{script_name()}({funcname()}.{lineno()}) | index file url => {index_download_url}','grey')

        ## dl , download
        dl_dict = self.get_filelist(index_download_url)

        ## file & directory remove
        self.as_file_remove(os.path.join(self.db_path, self.restore_path), file_opt=True)
        if 'CID' in dl_dict:
            chain_id = dl_dict['CID']
            self.as_file_remove(os.path.join(self.db_path, chain_id), file_opt=False)
            #self.as_file_remove(os.path.join(f'/app/goloop/data_test', chain_id), file_opt=False)
            del dl_dict['CID']

        dirusage = self.dir_free_size(self.db_path)

        ## dir size free size check
        if dirusage > diskcheck_per:
            self.send_slack(f"Not enough disk space : {dirusage:.2f}", "error")
            raise ValueError(f"Not enough disk : {dirusage:.2f}")
        else:
            cprint(f"{script_name()}({funcname()}.{lineno()}) | You have enough disk space : {dirusage:.2f} % ", 'yellow')

        ### backup file download
        for f_url, cksum_value in dl_dict.items():
            download_url = f'{self.s3_bkurl}/{f_url}'
            ### Thread off
            self.file_download(download_url,os.path.join(self.db_path,self.restore_path),cksum_value)

            ### Thread on
            #t = threading.Thread(
            #        target=self.file_download,
            #        args = (
            #            download_url,
            #            os.path.join(self.db_path,self.restore_path),
            #            cksum_value
            #        )
            #    )
            #t.start()

        ####  Thread 종료 체크
        #while t.is_alive():
        #    time.sleep(0.5)
        #    print(f'\rThread running',end='')
        #else:
        #    t.join()
        #    print(f'\rThread finished')
        #    pass

        self.db_file_decompress()

        run_elapsed = default_timer() - run_start_time
        run_time_completed_at = "{:5.3f}s".format(run_elapsed)
        output.cprint(f"\n\n>>>> for_time_completed_at = {run_time_completed_at}\n", 'yellow')

    ### send result slack
    def send_slack(self, msg_text=None, msg_level="info"):
        if self.is_send and msg_text:
            output.send_slack(
                url=self.send_url,
                msg_text=msg_text,
                msg_level=msg_level
            )

    # Restore WorkDir Create
    def createFolder(self, directory):
        try:
            if not os.path.exists(directory):
                os.makedirs(directory)
                cprint(f"++ {script_name()}({funcname()}.{lineno()}) | create : {directory}", "green")
        except OSError:
            raise OSError(f"{script_name()}({funcname()}.{lineno()}) | Error: Creating directory fail. : {directory}")

    ### Old file remove
    def as_file_remove(self, delete_path, file_opt=False):
        ## /app/goloop/data/{CID} , ## /app/goloop/data/[restore]/*.tar*
        delete_dir = os.path.join(delete_path)
        cprint(f'-- {script_name()}({funcname()}.{lineno()}) | Delete_dir : {delete_dir}', 'yellow')

        try:
            if file_opt :
                ### Delete directory file
                filelist = os.listdir(f"{delete_dir}")
                for item in filelist:
                    if f".tar.zst" in item:
                        os.remove(os.path.join(delete_dir, item))
                        cprint(f"-- {script_name()}({funcname()}.{lineno()}) | delete : {delete_dir} {item}", "red")
            else:
               ## Delete directory
               if os.path.isdir(delete_dir):
                   shutil.rmtree(delete_dir)
                   #os.rmdir(delete_dir)
                   cprint(f"-- {script_name()}({funcname()}.{lineno()}) | delete : {delete_dir}", "red")
               else:
                   cprint(f"-- {script_name()}({funcname()}.{lineno()}) | Not found {delete_dir}", "yellow")
        except OSError:
            raise OSError(f"{script_name()}({funcname()}.{lineno()}) | Error: file_remove ({file_opt})")

    ### dir size
    def get_dir_size(self, path):
        total = 0
        with os.scandir(path) as it:
            for entry in it:
                if entry.is_file():
                    total += entry.stat().st_size
                elif entry.is_dir():
                    total += self.get_dir_size(entry.path)
        return total

    def dir_free_size(self, path):
        dirsize = dirusage = 0
        total, used, free = shutil.disk_usage(path)
        dirsize = self.get_dir_size(path)
        #### 남은 공간 대비 db 디렉토리 사용량 (퍼센트)
        self.dirusage = dirsize / free * 100.0
        return self.dirusage

    ## MD5 HASH
    def getHash(self, path, blocksize=65536):
        afile = open(path, 'rb')
        hasher = hashlib.md5()
        buf = afile.read(blocksize)
        while len(buf) > 0:
            hasher.update(buf)
            buf = afile.read(blocksize)
        afile.close()
        return hasher.hexdigest()

    ### s3 response time check
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
            cprint(f"{script_name()}({funcname()}.{lineno()}) | get_connect_time error : {url} -> {sys.exc_info()[0]} / {e}", "red")
        return {"url": url, "time": elapsed_time, "name": name, "text": response_text, "status": status_code}

    def find_fastest_region(self):
        results = {}
        pool = ThreadPool(8)
        i = 0

        spinner = Halo(text=f"Finding fastest region", spinner='dots')
        spinner.start()

        check_file = 'route_check'

        for region_name, region_code in region_info.items():
            #URL = f'https://icon2-backup{region_code}.amazonaws.com/{check_file}'
            URL = f'https://{self.bucket_name_prefix}{region_code}.amazonaws.com/{check_file}'
            exec_func = "get_connect_time"
            exec_args = (f"{URL}", f"name={region_name}")
            #cprint(f'url => {URL} \t, exec_func_name = {exec_func}' , 'green')
            results[i] = {}
            #results[i]["data"] = pool.apply_async(getattr(sys.modules[__name__], exec_func), exec_args)
            results[i]["data"] = pool.apply_async(self.get_connect_time, args = exec_args)
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
        spinner.succeed(f'[Done] Finding fastest region')

        return last_latency

    ###  S3에있는  Backup  list 가져오기
    def get_filelist(self, file_url):
        try:
            ## get filelist.txt
            res = requests.get(file_url)
            filelist_text = res.text.strip().split('\n')
            filelist_url = f'{self.s3_bkurl}/{filelist_text[-1]}'
        except Exception as e:
            cprint(f"{script_name()}({funcname()}.{lineno()}) | {e}","red")

        try:
            dl_file_list = requests.get(filelist_url)
            self.f_dict = dl_file_list.json()
        except Exception as e:
            cprint(f"{script_name()}({funcname()}.{lineno()}) | {e}","red")
        return  self.f_dict

    ## S3에 업로드된 파일과 다운로드 된 파일 의 MD5 체크섬 비교
    def download_diff(self, download_file, orig_hash):
        localfile_hash = self.getHash(download_file)
        if localfile_hash == orig_hash :
            hash_rst = "ok"
        else:
            hash_rst = "nok"
        return hash_rst

    ##  파일 다운로드
    def file_download(self, download_url, download_path, hash_value):

        cprint(f'{script_name()}({funcname()}.{lineno()}) | download_url => {download_url} | download_path => {download_path}','yellow')
        try :
            local_dl_file = os.path.join(download_path,download_url.split("/")[-1])
            if os.path.isfile(local_dl_file) :
                diff_rst = self.download_diff(local_dl_file,hash_value)
            else:
                diff_rst = None


            if diff_rst == 'nok' or diff_rst is None:
                start_time = default_timer()

                #axel_option = f"-k -n {get_nproc} --verbose"    ###  axel 2.4 버전에서는 -k 옵션이 제외됨.
                axel_option = f"-n {self.get_nproc} --verbose"
                axel_cmd = f'axel {axel_option} {download_url} -o "{download_path}"'
                run_stat = base.run_execute(axel_cmd, capture_output=True)

                elapsed = default_timer() - start_time
                time_completed_at = "{:5.3f}s".format(elapsed)

                diff_rst = self.download_diff(local_dl_file,hash_value)
                if diff_rst == 'ok':
                    output.cprint(f'\n\t{threading.get_ident()} | {download_url.split("/")[-1]} |{diff_rst} | time_completed_at = {time_completed_at}', 'green')
                else:
                    raise ValueError(f"{script_name()}({funcname()}.{lineno()}) | download file Checksum Check Fail - '{download_file}'")
            else:
                output.cprint(f'\n\t{threading.get_ident()} | {download_url.split("/")[-1]} |exist file (checksum is Same)', 'green')
        except Exception as e:
            cprint(f"{script_name()}({funcname()}.{lineno()}) | {e}","red")


    def db_file_decompress(self):
        comp_algorithm = 'pzstd'

        os.chdir(self.db_path)
        if os.path.isdir(self.db_path):
            sour_dir = os.path.join(self.db_path, self.restore_path)
            cmd = f"cat {sour_dir}/*tar.* | {comp_algorithm} -cd | tar -xf - "

        #### test directory
        #os.chdir(f'{self.db_path}_test')
        #if os.path.isdir(f'{self.db_path}_test'):
        #    sour_dir = os.path.join(self.db_path, self.restore_path)
        #    cmd = f"cat {sour_dir}/*tar.* | {comp_algorithm} -cd | tar -xf - -C {self.db_path}_test"

        cprint(f"{script_name()}({funcname()}.{lineno()}) | cmd = {cmd}", 'yellow')

        if base.run_execute(cmd).get("stderr"):
            raise OSError(f"{script_name()}({funcname()}.{lineno()}) | Failed Decompression - '{cmd}'")



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