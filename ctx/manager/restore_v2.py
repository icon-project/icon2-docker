#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import threading
import sys, os
import time, datetime , json
import shutil, hashlib
import inspect
import re
import requests
import boto3
from multiprocessing.pool import ThreadPool
from halo import Halo
from boto3.s3.transfer import TransferConfig
from botocore.handlers import disable_signing
from timeit import default_timer

### 상위 모듈 import 하기 위한 경로 추가(?)
parent_dir = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
sys.path.append(parent_dir)
sys.path.append(parent_dir+"/..")

from config.configure import Configure
from common import converter, output, base
from common.converter import region_info as region_s3_info     ### regeion config
from common.converter import region_cf_info                    ### regeion config

sys.excepthook = output.exception_handler

## SSL Warnning 
base.disable_ssl_warnings()

filename = __file__
get_filename = filename.split('/')[-1]

def line_info(return_type=None):
    '''
       common/output.py 안에 추가 할 예정 
       추가 할 경우  import 필요 
       from common.output import line_info
       - line number 및 fucntion 위치를 출력하기 위함
    '''
    ### line number
    cf = inspect.currentframe()
    linenumber = cf.f_back.f_lineno
    
    ### Call to Function name
    func_name = cf.f_back.f_code.co_name
    
    ### file name
    frame = inspect.stack()[1]
    module = inspect.getmodule(frame[0])
    #filename = module.__file__
    #get_filename = filename.split('/')[-1]
    
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
    '''
      log 및 print를 하기 위한 함수
    '''
    color = color if color else f'green'
    level = level if level else f'INFO'

    now_time = (datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3])
    output.c_print(f'[{now_time}] [{level:5}] | {msg}', color)


class Restore:
    def __init__(self, 
        region="kr",                              ### 사용안함
        db_path=None,                             ### .settings.icon2.GOLOOP_NODE_DIR
        network="MainNet",                        ### .settings.env.SERVICE
        send_url=None,                            ###  사용자 입력   /  없어도무방   .settings.env.RESTORE_SEND_URL
        bucket_name_prefix="icon2-backup",        ###  사용자 입력(docker 변수로 ) 없을 경우 defaut 사용  : false
        download_type="multi",                    ### 변경 필요 없음
        download_path='restore',                  ### Download directory | 사용자 입력(docker 변수로) 없을 경우 defaut 사용  : false
        download_url='download.solidwallet.io',   ### Downlaod type check  s3 or cloud front , Default : s3 download
        download_url_type='s3',                   ### Downlaod type check  s3 or cloud front , Default : s3 download , "s3" or "[cf | cloudfront]"
        download_tool='axel',                     ### Download Tool command option .  Default Axel command  [ axel | aria2(aria2c) ]
        download_force=False                      ### Download file이 동일할경우에 대한 액션 True일 경우 모두 삭제 후 download /
                                                  ### False일 경우 동일 파일 비교 후 다를 경우 삭제 |  사용자 입력(docker 변수로 ) 없을 경우 defaut 사용  : false
    ):
        self.region = region                            ### 사용안함
        self.db_path = db_path                          # 필수 Default => icon2 : /app/goloop
        self.network = network                          # 필수  Blockchain  node network name
        self.bucket_name_prefix = bucket_name_prefix    # 필수 

        self.download_path = download_path              # Change variable name restore_path to download_path
        self.download_filename = ""
        self.download_url = re.sub('(http|https)://','',download_url)
        self.download_url_type = download_url_type
        self.download_type = download_type              ### 사용안함
        self.download_force = download_force
        self.download_tool = download_tool              ####  Default axel 
        self.verbose = None

        ### Send url check 
        self.send_url = send_url                        ### 없어도 무방
        if send_url:
            self.is_send = True
        else:
            self.is_send = False

        ##  Icon2 node DB Path check 
        if self.db_path is None or not output.is_file(self.db_path):
            raise ValueError(f"-- {line_info()} | | db_path not found - '{self.db_path}'")

        self.get_nproc = ''.join(base.run_execute('nproc', capture_output=True)['stdout'])    

        ### disk usage check percent 
        self.diskcheck_per = 70

        self.run()

    ####  class main run function
    def run(self):
        ### running start time check 
        run_start_time = default_timer()

        ## Downlaod(Restore) WorkDir Create
        self.restore_path = os.path.join(self.db_path, self.download_path)
        self.createDirectory(self.restore_path)  

        ####  S3 또는 Cloudfront URL check 
        self.download_url_type_check()

        ## fastest region check
        last_latency_rst = self.find_fastest_region()
        log_print(f'++ {line_info()} | | {last_latency_rst}', 'grey')

        self.s3_bkurl = last_latency_rst.replace('/route_check','')
        ### ex)  s3         : https://icon2-backup-kr.amazon.com/
        ### ex)  Cloudfront : https://download.soliwallet.io/kr/bk/
        log_print(f'++ {line_info()} | {self.s3_bkurl}', 'grey')

       	## get index.txt
        index_download_url = f'{self.s3_bkurl}/{self.network}/index.txt'
        log_print(f'++ {line_info()} | index file url => {index_download_url}','grey')

        ## dl , download   url_addr == self.dl_url
        self.dl_dict, self.url_addr = self.get_filelist(index_download_url)        

        ### CID & Disk free size check & as_Download BackupFile Delete
        self.run_prejob(self.dl_dict)
        
        ## Backup file download
        self.get_bkfile(self.url_addr, self.dl_dict)

        self.db_file_decompress()

        ### Finished time check 
        run_elapsed = default_timer() - run_start_time
        run_time_completed_at = "{:5.3f}s".format(run_elapsed)
        log_print(f"\n\n>>>> for_time_completed_at = {run_time_completed_at}\n", 'yellow')


    ####### >>>>>>>
    ### send result slack
    def send_slack(self, msg_text=None, msg_level="info"):
        if self.is_send and msg_text:
            output.send_slack(url=self.send_url, msg_text=msg_text, msg_level=msg_level)

    # Download(restore) Work Directory Create
    def createDirectory(self, dir_name):
        try:
            if not os.path.exists(dir_name):
                os.makedirs(dir_name)
                log_print(f"++ {line_info()} | create : {dir_name}", "green")
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
            log_print(f"-- {line_info()} | get_connect_time error : {url} -> {sys.exc_info()[0]} / {e}", "red")
        return {"url": url, "time": elapsed_time, "name": name, "text": response_text, "status": status_code}

    ### Check fast aws region
    def find_fastest_region(self):
        ## worker Thread Setting 
        worker_thread_cnt = 8 
        pool = ThreadPool(worker_thread_cnt) 

        results = {}
        i = 0

        spinner = Halo(text=f"Finding fastest region", spinner='dots')
        spinner.start()

        check_file = 'route_check'

        for region_name, region_code in self.region_info.items():
            dl_addr = re.sub('_regioncode',region_code,self.dl_url)  ## region code 치환
            URL = f'{dl_addr}' + f'/{check_file}'
            #exec_func = "get_connect_time"
            exec_args = (f"{URL}", f"name={region_name}")
            results[i] = {}
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
        spinner.succeed(f'++ {line_info()} | [Done] Finding fastest region')

        #return last_latency
        return last_latency["url"]

    #### get download backup file list
    def get_filelist(self, file_url):
        print(file_url)
        try:
            ## get filelist.txt
            res = requests.get(file_url)
            filelist_text = []
            temp_list = res.text.strip().split('\n')     ### 마지막 라인이 공백일 경우 제거
            print(temp_list)

            for flist in temp_list:
                if re.match(self.match_keyword, flist):
                    filelist_text.append(flist)
            #file_text = filelist_text[-1].replace(f'{self.region_code}/bk/','')
            self.dl_url =  re.sub('/[\w]+/bk','',file_url).replace(f'/{self.network}/index.txt','')
            filelist_url = f'{self.dl_url}/{filelist_text[-1]}'
            log_print(f"++ {line_info()} | {filelist_url}","blue")
        except Exception as e:
            log_print(f"-- {line_info()} | {e}","red")

        try:
            #log_print(f"++ {line_info()} | {filelist_url}","green")
            dl_file_list = requests.get(filelist_url)
            self.f_dict = dl_file_list.json()
        except Exception as e:
            log_print(f"-- {line_info()} | {e}","red")

        return  self.f_dict, self.dl_url

    def run_prejob(self, dl_info):
        ### chain id check 
        if 'CID' in dl_info:
            chain_id = dl_info['CID']
            del_dir_list = ['contract','db', 'wal', 'genesis.zip']
            for del_item in del_dir_list:
               dellist = os.path.join(self.db_path, chain_id, del_item)
               self.as_file_remove(dellist, file_opt=False)
            del dl_info['CID']

        ### free disk size check 
        if 'Total_size' in dl_info:
            total, used, p_free = shutil.disk_usage(self.db_path)
            DL_Total_Size = dl_info['Total_size'].split(' ')[0]
            if float(DL_Total_Size) * 1.5 < float(p_free) :
                log_print(f"++ {line_info()} | You have enough disk space ", 'yellow')
                del dl_info['Total_size']
            else:
                raise ValueError(f"++ {line_info()} | Not enough disk - Download size : {DL_Total_Size} Byte , Disk Free Size : {p_free} Byte")
        else :
            dirusage = self.dir_free_size(self.db_path)
            ## dir size free size check
            if dirusage > self.diskcheck_per:
                self.send_slack(f"Not enough disk space : {dirusage:.2f}", "error")
                raise ValueError(f"-- {line_info()} | Not enough disk : {dirusage:.2f}")
            else:
                log_print(f"++ {line_info()} | You have enough disk space : {dirusage:.2f} % ", 'yellow')

        ### Download force delete ( Old Backup File Delete)
        if self.download_force:
            dl_path = os.path.join(self.db_path, self.download_path)
            del_list = os.listdir(dl_path)
            for delfile in del_list:
                if f'tar.zst' in delfile :
                    log_print(f'Delete Old Backup file  : {os.path.join(dl_path,delfile)}', 'red')
                    os.remove(os.path.join(dl_path,delfile))


    def get_bkfile(self, get_url, dl_info):           
        ### backup file download
        for f_url, cksum_value in dl_info.items():
            download_url = f'{get_url}/{f_url}'
            ### Thread off
            #self.file_download(download_url,os.path.join(self.db_path,self.restore_path),cksum_value)

            ## Thread on
            t = threading.Thread(
                    target=self.file_download,
                    args = (
                        download_url,
                        os.path.join(self.db_path,self.restore_path),
                        cksum_value
                    )
                )
            t.start()

        log_print(f"++ {line_info()} | Download job wait ....", 'green')

        mainThread = threading.currentThread()
        for thread in threading.enumerate():
            log_print(f'{thread}', 'red')
            if thread is not mainThread:
                thread.join()
        log_print(f"++ {line_info()} | Download job finished", 'green')        

    ##  파일 다운로드
    def file_download(self, download_url, download_path, hash_value):

        log_print(f'++ {line_info()} | download_url => {download_url} |\n\t\t\tdownload_path => {download_path}','yellow')
        try :
            local_dl_file = os.path.join(download_path, download_url.split("/")[-1])

            ## Old Download file Delete check 
            if self.download_force:
                if os.path.isfile(local_dl_file):
                    log_print(f'>>> delete |    {local_dl_file}', 'red')
                    os.remove(local_dl_file)

            if os.path.isfile(local_dl_file) :
                diff_rst = self.download_diff(local_dl_file,hash_value)
                if diff_rst == 'nok' :
                    os.remove(local_dl_file)
                    log_print(f'-- {threading.get_ident()} | {download_url.split("/")[-1]} |{diff_rst} |delete : {local_dl_file} ', 'red')
                    diff_rst = None
            else:
                diff_rst = None


            if diff_rst is None:
                start_time = default_timer()

                if self.download_tool == 'axel' or self.download_tool is None:
                    #axel_option = f"-k -n {get_nproc} --verbose"    ###  axel 2.4 버전에서는 -k 옵션이 제외됨.
                    axel_option = f"-n {self.get_nproc} --verbose"
                    download_cmd = f'axel {axel_option} {download_url} -o "{download_path}"'
                elif self.download_tool == 'aria2' or  self.download_tool == 'aria2c':
                    aria2_option = f'-j {self.get_nproc}'
                    download_cmd = f'aria2c {aria2_option} {download_url} -d {download_path}'

                run_stat = base.run_execute(download_cmd, capture_output=True)

                elapsed = default_timer() - start_time
                time_completed_at = "{:5.3f}s".format(elapsed)

                diff_rst = self.download_diff(local_dl_file,hash_value)
                if diff_rst == 'ok':
                    log_print(f'\n\t{threading.get_ident()} | {download_url.split("/")[-1]} |{diff_rst} | time_completed_at = {time_completed_at}', 'green')
                else:
                    raise ValueError(f"++ {line_info()} | download file Checksum Check Fail - '{download_file}'")
            else:
                log_print(f'\n\t{threading.get_ident()} | {download_url.split("/")[-1]} |exist file (checksum is Same)', 'green')
        except Exception as e:
            log_print(f"-- {line_info()} | {e}","red")

    ### Old file remove
    def as_file_remove(self, delete_path, file_opt=False):
        ## /app/goloop/data/{CID} , ## /app/goloop/data/[restore]/*.tar*
        delete_dir = os.path.join(delete_path)
        log_print(f'-- {line_info()} | Delete_job_dir : {delete_dir}', 'yellow')

        try:
            if file_opt :
                ### Delete directory file
                filelist = os.listdir(f"{delete_dir}")
                for item in filelist:
                    if f".tar.zst" in item:
                        os.remove(os.path.join(delete_dir, item))
                        log_print(f"-- {line_info()}| delete : {delete_dir} {item}", "red")
            else:
               p_rst = f'deleted : {delete_dir}"'
               p_color = 'red'
               ## Delete directory
               if os.path.isdir(delete_dir):
                   shutil.rmtree(delete_dir)
                   lineinfo = f'{line_info()}'
               elif os.path.isfile(delete_dir):
                   os.remove(os.path.join(delete_dir))
                   lineinfo = f'{line_info()}'
               else:
                   p_rst = f'Not found {delete_dir}'
                   p_color = 'yellow'
                   lineinfo = f'{line_info()}'
               log_print(f"{lineinfo} | {p_rst}", p_color)

        except OSError:
            raise OSError(f"-- {line_info()} | Error: file_remove ({file_opt})")

    ## S3에 업로드된 파일과 다운로드 된 파일 의 MD5 체크섬 비교
    def download_diff(self, download_file, orig_hash):
        localfile_hash = self.getHash(download_file)
        if localfile_hash == orig_hash :
            hash_rst = "ok"
        else:
            hash_rst = "nok"
        return hash_rst

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

    def db_file_decompress(self):
        log_print(f'++ {line_info()} | decompress start', 'yellow')
        comp_algorithm = 'pzstd'
        old_run_path = os.getcwd()

        if os.path.isdir(self.db_path):
            os.chdir(self.db_path)
            log_print(f'+++ {line_info()} | change job directory is \"{self.db_path}\"', 'yellow')
            sour_dir = os.path.join(self.db_path, self.restore_path)
            cmd = f"cat {sour_dir}/*tar.* | {comp_algorithm} -cd | tar -xf - -C {self.db_path}"

        log_print(f'++ {line_info()} | cmd = {cmd}', 'yellow')

        if base.run_execute(cmd).get("stderr"):
            raise OSError(f"-- {line_info()} | Failed Decompression - '{cmd}'")

        ### 이전  디렉토리로  변경
        os.chdir(old_run_path)
        

    ####### <<<<<<


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
    from config.configure import Configure as CFG

    #test config  json download url  : https://d1hfk7wpm6ar6j.cloudfront.net/SejongNet/default_configure.json
    ###  test path & file   : /goloop/default_configure.json
    use_file=True
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
    icon2_config = config['settings']['icon2']
    env_config = config['settings']['env']
    # compose_env_config = config['settings']['env']['COMPOSE_ENV']

    ### Goloop DB PATH
    if icon2_config.get('GOLOOP_NODE_DIR') :
        db_path = icon2_config['GOLOOP_NODE_DIR']
    else :
        default_db_path = 'data'
        # base_dir = compose_env_config['BASE_DIR']
        base_dir = env_config['BASE_DIR']
        db_path = os.path.join(base_dir, default_db_path)


    ### Restore Options 
    ### network  =  MainNet | SejongNet ....
    # network = env_config['SERVICE']  if env_config.get('SERVICE') else compose_env_config['SERVICE']
    # restore_path = env_config['RESTORE_PATH']  if env_config.get('RESTORE_PATH') else compose_env_config['RESTORE_PATH']
    # dl_force = env_config['DOWNLOAD_FORCE']  if env_config.get('DOWNLOAD_FORCE') else compose_env_config['DOWNLOAD_FORCE']
    # download_tool = env_config['DOWNLOAD_TOOL']  if env_config.get('DOWNLOAD_TOOL') else compose_env_config['DOWNLOAD_TOOL']
    # download_url = env_config['DOWNLOAD_URL']  if env_config.get('DOWNLOAD_URL') else compose_env_config['DOWNLOAD_URL']
    # download_url_type = env_config['DOWNLOAD_URL_TYPE']  if env_config.get('DOWNLOAD_URL_TYPE') else compose_env_config['DOWNLOAD_URL_TYPE']
    network = env_config['SERVICE']
    restore_path = env_config['RESTORE_PATH']
    dl_force = env_config['DOWNLOAD_FORCE']
    download_tool = env_config['DOWNLOAD_TOOL']
    download_url = env_config['DOWNLOAD_URL']
    download_url_type = env_config['DOWNLOAD_URL_TYPE']

    print(f'db_path = {db_path}')
    print(f'network = {network}')
    print(f'restore_path = {restore_path}')

    print(f'dl_force = {dl_force}')
    print(f'download_tool = {download_tool}')
    print(f'download_url = {download_url}')
    print(f'download_url_type = {download_url_type}')



    Restore(
        db_path=db_path,
        network=network,
        download_path=restore_path,
        download_force=dl_force,
        download_url=download_url,
        download_tool=download_tool,
        download_url_type=download_url_type
    )

if __name__ == '__main__' :
    main()
