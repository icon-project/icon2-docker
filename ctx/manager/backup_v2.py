#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys, os, datetime, inspect
from datetime import datetime
import threading
import shutil
import requests
import hashlib
import json
import boto3
from boto3.s3.transfer import TransferConfig
from botocore.handlers import disable_signing
from timeit import default_timer

parent_dir = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
sys.path.append(parent_dir)
sys.path.append(parent_dir+"/..")
from common import converter, output, base

## SSL Warnning
sys.excepthook = output.exception_handler

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
    output.cprint(f'[{now_time}] [{level.upper():5}] | {msg}', color)


def s3sync_upload(profile_name='default', source_dir='./',destination_dir='./', prefix=None, opt_output_path='./'):

    aws_profile_name = profile_name
    s3_bucket_path = f's3://{destination_dir}'
    s3_exclude_opt = ["--delete"]
    s3_exclude_word = ["ee.sock","cli.sock","*.sock","*rconfig.json","*auth.json","*temp","*restore"] 
    for excludeword in s3_exclude_word:
       s3_exclude_opt.append(f'--exclude="{excludeword}"')
        
    s3_exclude = ' '.join(s3_exclude_opt)
    s3sync_cmd = f'aws --profile {aws_profile_name} s3 sync {source_dir} {s3_bucket_path} {s3_exclude}'
    run_stat = base.run_execute(s3sync_cmd, capture_output=False)

    #### s3sync upload file indexing
    import bk_file_indexcing as indexing

    indexing_dir = source_dir                                                       ### indexing Directory
    #in_file_prefix=f'http://download.soliwallet.io/kr/bk/MainNet/20211012/1700'    ### index file 안에 등록될 다운로드 주소 
    in_file_prefix = prefix if prefix else f'http://localhost'                      ### index file 안에 등록될 다운로드 주소 
    in_file_ouptput_path=opt_output_path                                            ### index file 안에 등록될 output path
    
    index_file = indexing.FileIndexer(
                        base_dir=indexing_dir, 
                        debug=True, 
                        check_method='size', 
                        prefix=in_file_prefix,
                        output_dir=in_file_ouptput_path
                ).run()

    return run_stat, index_file
    

class Backup:
    def __init__(
        self,
        core_version="core2",
        profile="default",
        region="jp",
        upload_type="multi",
        download_url_type='s3',
        download_url = None,
        bucket_name_prefix="icon2-backup-",
        network="MainNet",
        ipaddr='localhost',
        docker_path="/app/goloop",
        docker_file="docker-compose.yml",
        comp_job_dir='temp',
        control_chain = False,
        db_path=None,
        backup_path=None,
        send_url=None,
        is_mig_db = False,
        ):

        self.profile = profile                          ### AWS profile name (default  : defualt)
        self.region = region                            ### AWS Region info  (default : jp)
        self.upload_type = upload_type                  ### AWS upload type [ multi | single | sync ] (default : multi)
        self.download_url_type = download_url_type      ### AWS download url type [ s3 | cf | sync ] (default : s3)
        self.download_url = download_url                ### Download url address in the indexing file.
        self.bucket_name_prefix = bucket_name_prefix    ### AWS S3 Bucket prefix name (default : icon2-backup-)

        self.control_chain = control_chain              ### Icon node control_chain cmd True (default : false) / True : enable , False : disable
        self.db_path = db_path                          ### Icon Node levelDB or RocksDB PATH
        self.backup_path = backup_path                  ### DB Compression Parant PATH
        self.comp_job_dir = comp_job_dir                ### DB Compress job path 
        self.network = network                          ### Icon Node info [ MainNet | testnet | .... ] (default : MainNet)
        self.send_url = send_url                        ### Script running Fail noti slack url (default : None)
        self.upload_filename = ""                       ### compression name 

        self.docker_path = docker_path                  ### Docker-compose running path (default : /app/goloop)
        self.docker_file = docker_file                  ### Docker-compose file name 
        self.core_version = core_version                ### icon node version (default : icon2)
        self.ipaddr = ipaddr                            ### node status Check IP (default : localhost)


        self.is_mig_db = is_mig_db                      ### Icon1 to Icon2 Migration DB upload (default : False)   upload is True option 
        if self.is_mig_db.lower() == 'true':
            self.is_mig_db = True
        elif self.is_mig_db.lower()  == 'false':
            self.is_mig_db = False

        print (f'self.is_mig_db : {self.is_mig_db} ///   {type(self.is_mig_db)}')

        ### Slack Noti URL Check 
        if send_url:
            self.is_send = True
        else:
            self.is_send = False

        ### control_chain cmd Check 
        print(f'control_chain : {control_chain} //// {type(control_chain)}')
        if self.control_chain:
            chain_cmd=f'control_chain -h'
            if base.run_execute(chain_cmd).get("stderr"):
                log_print(f'pkg install cmd \n==> "pip3 install socket_request --force-reinstall"', 'red')
                self.control_chain = False

        ### Node DB path Check : 없을 경우스ㅌ크립트 종료 
        if self.db_path is None or not output.is_file(self.db_path):
            raise ValueError(f"{line_info()} | Not found DB PATH - '{self.db_path}'")

        ### 백업 경로가 없을 경우 스크립트 종료??????
        if self.backup_path is None or not output.is_file(self.backup_path):
            self.createFolder(self.backup_path)
            #raise ValueError(f"{line_info()} | backup_path not found - '{self.backup_path}'")

        if self.download_url_type == "sync":
            if self.upload_type != "sync" :
                log_print(f'{line_info()} | Change variable  "self.upload_type : {self.upload_type} => sync"', 'green', 'info')
                self.upload_type = "sync"

        #### Disk 가용 공간체 임계치 
        self.diskcheck_per = 70

        self.run()


    ### >>>>>>

    # Backup WorkDir Create
    def createFolder(self, directory):
        try:
            if not os.path.exists(directory):
                os.makedirs(directory)
        except OSError:
            raise OSError("{line_info()} | Error: Creating directory. " + directory)

    # Node status Check 
    def get_loopchain_state(self, core_version='core2', ipaddr="localhost", port=os.environ.get("RPC_PORT", 9000)):
        try:
            #### Core type Check icon1(loopchain) or icon2(goloop)
            if core_version == 'core1':
                url = f"http://{ipaddr}:{port}/api/v1/status/peer"
                r = requests.get(url, verify=False, timeout=5)
                peer_status = r.json()["status"]
            else:
                url = f"http://{ipaddr}:{port}/admin/chain"
                r = requests.get(url, verify=False, timeout=5)
                peer_status = r.json()[0]["state"]

            ####  Icon Node status Check 
            if peer_status == "Service is online: 0" :
                self.block_height = r.json()["block_height"]
                self.nid = r.json()['nid'].replace("0x",'')
                log_print(f'++ {line_info()} | core_version : {core_version} / nid : {self.nid} ', 'green')
            elif peer_status == "started":
                self.cid = r.json()[0]['cid'].replace("0x",'')
                self.nid = r.json()[0]['nid'].replace("0x",'')
                self.block_height = r.json()[0]["height"]
                log_print(f'++ {line_info()} | core_version : {core_version} / cid : {self.cid} / nid : {self.nid} ', 'green')

            #### Icon node BlockHeight Check 
            if self.block_height:
                log_print(f'++ {line_info()} | core_version : {core_version} | Block_Height : {self.block_height}', 'green')
                self.upload_filename = f"{self.network}_BH{self.block_height}_data-{converter.todaydate('file')}.tar.zst"
            else:
                error_keyword = f"Please check the peer status. : {peer_status}"
                log_print(error_keyword,'red')
                self.send_slack(error_keyword, "error")
                raise RuntimeError(error_keyword)
        except:
            except_keyword = f"Please check the node status. :  {url}"
            self.send_slack(except_keyword, "error")
            raise RuntimeError(except_keyword)

        return self.block_height if core_version == 'core1' else self.block_height, self.cid

    ### OLD File Delete 
    def as_file_remove(self):
        backup_dir = os.path.join(self.backup_path, self.comp_job_dir)
        filelist = os.listdir(f"{backup_dir}")
        for item in filelist:
            os.remove(os.path.join(backup_dir, item))
            log_print(f"-- {line_info()} | delete {backup_dir} {item}", 'red')

    ### directory size check 
    def get_dir_size(self, path):
        total = 0
        with os.scandir(path) as it:
            for entry in it:
                if entry.is_file():
                    total += entry.stat().st_size
                elif entry.is_dir():
                    total += self.get_dir_size(entry.path)
        return total

    #### s3 or cloudfron에 압축파일 형태로 올리고자 할 경우 사용 
    def compress_prejob(self):
        # As-is Backup File Delete
        self.as_file_remove()

        total, used, free = shutil.disk_usage(self.backup_path)
        dirsize = self.get_dir_size(self.db_path)
        #### 남은 공간 대비 db 디렉토리 사용량 (퍼센트)
        dirusage = dirsize / free * 100.0

        if dirusage > self.diskcheck_per:
            self.send_slack(f"Not enough disk space : {dirusage:.2f}", "error")
            raise ValueError(f"{line_info()} | Not enough disk : {dirusage:.2f} %")
        else:
            log_print(f"++ {line_info()} | You have enough disk space : {self.backup_path} usage => {dirusage:.2f} %", 'yellow')

    #### Docker stop or start / Control_chain stop/start
    def run_peer(self, run_path, dc_file, run_mode):
        ## run mode
        run_mode = run_mode.lower()

        if self.control_chain :
            run_cmd=f'control_chain {run_mode}'
        else :
            os.chdir(run_path)

            ## docker-compose config file exist check
            if os.path.isfile(os.path.join(run_path,dc_file)) is False :
                docker_files = [ file for file in os.listdir(run_path) if file.endswith(".yml") ]
                if len(docker_files) > 1 :
                    fileNameAndTimeList = []
                    for file in docker_files :
                        file_mtime = os.path.getmtime(file)
                        fileNameAndTimeList.append((file,file_mtime))
                    sortlist = sorted(fileNameAndTimeList, key=lambda x: x[1], reverse=True)
                    dc_file = sortlist[0][0]
                elif len(docker_files) == 1 :
                    dc_file = docker_files[0]
                else :
                    log_print(f'-- {line_info()} | Not found \"{os.path.join(run_path,"docker-compose.yml")}\"', 'red')
                    raise SystemExit()

            docker_cmd = 'docker-compose'
            docker_ops = f' -f {dc_file}'

            if run_mode == "start" or run_mode == "up" :
                run_cmd = docker_cmd + docker_ops + " up -d"
            elif run_mode == "stop" or run_mode == "down" :
                run_cmd = docker_cmd + docker_ops + " down"
            elif run_mode == "status":
                run_cmd = f'{docker_cmd} + "ps"'
            else :
                log_print(f'-- {line_info()} | Not found run_mode : {run_mode}  - [start|stop|status]', 'green')
                raise SystemExit()

        run_stat = base.run_execute(run_cmd, capture_output=False)
        
        return run_stat

    #### DB Compress
    def db_file_compress(self):

        chain_id = self.cid
        os.chdir(self.db_path)
        
        tar_exclude_opt = ''
        tar_exclude_list = []
        for exlist in tar_exclude_list:
            tar_exclude_opt += f'--exclude {exlist} '
        
        comp_algorithm = 'pzstd'
        
        tar_split_size = 1000                ### Unit : MB
        tar_split_opt = f'split -b {tar_split_size}m'
        
        if os.path.isdir(self.db_path) :
            total_comp_size = 0
            sour_dir = os.path.join(self.backup_path, self.comp_job_dir)
            # cmd = f"tar -I pigz -cf {upload_filename} {db_dir[0]} {db_dir[1]}"
            cmd = f"tar {tar_exclude_opt} -cf - {chain_id} | {comp_algorithm} | {tar_split_opt} - {sour_dir}/{self.upload_filename}"
            log_print(f"++ {line_info()} | cmd = {cmd}" , 'yellow')
        
            if base.run_execute(cmd).get("stderr"):
            # if os.system(f"{cmd}") is not 0:
                self.send_slack(f"Compress Failed : {cmd}", "error")
                raise OSError(f"{line_info()} | Failed compression - '{cmd}'")
        
            filelist = os.listdir(f"{sour_dir}")
            for i, flist in enumerate(filelist):
                if f".tar.zst" in flist:
                    fp = os.path.join(sour_dir,flist)
                    file_info = os.stat(fp)
                    #log_print(f'file name : {fp}, {file_info.st_size}', 'yellow')
                    total_comp_size += int(file_info.st_size)
        
            if total_comp_size :
                self.total_comp_size = total_comp_size
            else :
                self.total_comp_size = None

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


    def send_slack(self, msg_text=None, msg_level="info"):
        if self.is_send and msg_text:
            output.send_slack(
                url=self.send_url,
                msg_text=msg_text,
                msg_level=msg_level
            )

    def multi_part_upload_with_s3(self, filename=None, key_path=None, region=None, upload_type="single"):
        start_time = default_timer()
        session = boto3.session.Session(profile_name=self.profile)

        if region is None or region == "":
            self.BUCKET_NAME = f"{self.bucket_name_prefix}kr"
        else:
            self.BUCKET_NAME = f"{self.bucket_name_prefix}{region}"

        ## region check
        if region == "hk":
            s3 = session.resource('s3', region_name="ap-east-1",)
        else:
            s3 = session.resource('s3',)

        # single parts
        if upload_type == "single":
            s3.meta.client.meta.events.register(
                'choose-signer.s3.*', disable_signing)
            config = TransferConfig(multipart_threshold=838860800, max_concurrency=10, multipart_chunksize=8388608,
                                    num_download_attempts=5, max_io_queue=100, io_chunksize=262144, use_threads=True)
            # multiparts mode -> AWS S3 CLI: Anonymous users cannot initiate multipart uploads
        elif upload_type == "multi":
            config = TransferConfig(multipart_threshold=1024 * 25, max_concurrency=10,
                                    multipart_chunksize=1024 * 25, use_threads=True)
        else:
            log_print(f"-- {line_info()} | Unknown upload_type-> {upload_type}", "red")
            raise SystemExit()

        if filename is None:
            log_print(f"-- {line_info()} | [ERROR] filename is None", "red")
            raise SystemExit()

        if key_path is None:
            key_path = filename

        try:
            s3.meta.client.upload_file(filename, self.BUCKET_NAME, key_path,
                                    # ExtraArgs={'ACL': 'public-read', 'ContentType': 'text/pdf'},
                                    Config=config,
                                    Callback=ProgressPercentage(filename)
                                    )
        except Exception as e:
            e = str(e).replace(":", ":\n")
            log_print(f"\n{line_info()} | [ERROR] File upload fail / cause -> {e}\n", "red")
            raise SystemExit()

        elapsed = default_timer() - start_time
        time_completed_at = "{:5.3f}s".format(elapsed)

        log_print(f"{line_info()} | {key_path} | {filename} |  {region} | {upload_type}", 'green')
        log_print(f"\n\t{threading.get_ident()} | {filename} |  time_completed_at = {time_completed_at}", 'green')

    def upload(self):
        cksum_dict = {}

        ### add CID info
        cksum_dict['CID'] = self.cid
        ### Total Backup file Size info  Unit Type : Byte
        if self.total_comp_size :
            cksum_dict['Total_size'] = f'{self.total_comp_size} Byte'

        sour_dir = os.path.join(self.backup_path, self.comp_job_dir)
        #### old config
        #dest_dir = f"{self.network}/{converter.todaydate()}/{converter.todaydate('hour')}"
        #index_dest_dir = f'{self.network}'

        #s3upload_path =  f'{self.region}/bk/mig_db' if self.is_mig_db == True else f'{self.region}/bk'
        ### honam

        if self.is_mig_db :  
            s3upload_path = f'{self.region}/bk/mig_db'
        else:
            s3upload_path = f'{self.region}/bk'

        dest_dir = f"{s3upload_path}/{self.network}/{converter.todaydate()}/{converter.todaydate('hour')}"
        index_dest_dir = f'{s3upload_path}/{self.network}'

        log_print(f"self.is_mig_db = {self.is_mig_db} /////  s3upload_path => {s3upload_path}", "red")
         
        for root, dirs, files in os.walk(sour_dir):
            for_start_time = default_timer()
            for filename in files:
                local_path = os.path.join(root, filename)
                s3_path = f"{dest_dir}/{filename}"
                try:
                    t = threading.Thread(
                        target=self.multi_part_upload_with_s3,
                        args=(
                            f"{local_path}",
                            s3_path,
                            self.region,
                            self.upload_type
                            )
                        )
                    t.start()
                    #self.multi_part_upload_with_s3(
                    #    f"{local_path}",
                    #    s3_path,
                    #    self.region,
                    #    self.upload_type
                    #)
                    md5hash = self.getHash(local_path)
                    cksum_dict[s3_path] = md5hash
                except Exception as e:
                    e = str(e).replace(":", ":\n")
                    log_print(f"\n {line_info()} | [ERROR] File upload fail / cause -> {e}\n", "red")

            t.join()

            ### Backup upload list & MD5hash Checksum value index file create / upload   >>>
            #print(json.dumps(cksum_dict, indent=4))
            index2_filename = 'filelist.json'
            index2_file = os.path.join(root, index2_filename)

            if os.path.isfile(index2_file):
                os.remove(index2_file)

            with open(index2_file, 'a') as f :
                    f.write(json.dumps(cksum_dict))

            pIndex_filename = 'index.txt'
            pIndex_file = os.path.join(root, pIndex_filename)

            index_info = {
                ## local_upload_file : s3_upload_path
                index2_file : f"{dest_dir}/{index2_filename}",
                pIndex_file : f"{index_dest_dir}/{pIndex_filename}"
            }

            for key, value in index_info.items():
                upload_file = key
                upload_s3_path = value
                if pIndex_filename in upload_file :
                    s3api_cmd = f'aws s3api list-objects --bucket {self.BUCKET_NAME}'
                    s3api_query = f'--prefix {index_dest_dir} --query \"Contents[?contains(Key, \'{index2_filename}\')].[Key]\" --output=text'
                    s3cmd = f'{s3api_cmd} {s3api_query} > {pIndex_file}'
                    log_print(f'++ {line_info()} | {s3cmd}','yellow')

                    base.run_execute(s3cmd, capture_output=False)
                    log_print(f'++ {line_info()} | pIndex_file : {pIndex_file}','yellow')

                self.multi_part_upload_with_s3(
                            upload_file,
                            upload_s3_path,
                            self.region,
                            self.upload_type
                )

            for_elapsed = default_timer() - for_start_time
            for_time_completed_at = "{:5.3f}s".format(for_elapsed)
            log_print(f"\n\n>>>> for_time_completed_at = {for_time_completed_at}\n", 'yellow')
        return True

    ##<<<<<<<<<<<<


    def run(self):
        
        self.createFolder(os.path.join(self.backup_path, self.comp_job_dir))         # Backup WorkDir Create
        self.get_loopchain_state(core_version=self.core_version, ipaddr=self.ipaddr) # Node Status Check

        ##### self.download_url_type이 sync 가 아닐 경우 이전 압축 파일 업로드 관련 로직 수행
        if self.download_url_type is not 'sync':
            self.compress_prejob()

        ##### control_chain 일 True일 경우 control_chain 명령어 실행
        self.run_peer(self.docker_path, self.docker_file, "stop")

        ##### self.download_url_type이 sync 가 아닐 경우 이전 압축 sync 일 경우 s3sync command 실행
        if self.download_url_type is not 'sync':
            self.db_file_compress()   # LevelDB File Compress
        else : 
            local_path=f'{self.db_path}/'
           
            if self.is_mig_db : 
                s3sync_path = f'{self.region}/bk/mig_db/s3sync'
            else:
                s3sync_path = f'{self.region}/bk/s3sync'


            log_print(f"\n\n>>>> self.is_mig_db : {self.is_mig_db}  /////  s3sync_path : {s3sync_path}\n", 'yellow')
            s3_path=f'{self.bucket_name_prefix}{self.region}/{s3sync_path}'

            run_stat , upload_indexfile = s3sync_upload(
                                               profile_name="default", 
                                               source_dir=local_path, 
                                               destination_dir=f'{s3_path}/{self.network}/',
                                               prefix=f'{self.download_url}/{self.network}', 
                                               opt_output_path=f'{os.path.join(self.backup_path, self.comp_job_dir)}'
                                           )
    
            #### indexing file upload
            local_upload_file = upload_indexfile
            upload_s3_name = f"{s3sync_path}/{self.network}/{upload_indexfile.split('/')[-1]}"
            self.multi_part_upload_with_s3(local_upload_file, upload_s3_name, self.region, upload_type='multi')

        ##### control_chain 일 True일 경우 control_chain 명령어 실행
        self.run_peer(self.docker_path, self.docker_file, "start")

        ##### self.download_url_type이 sync 가 아닐 경우 파일 업로드
        if self.download_url_type is not 'sync':
            self.upload()

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

def parse_args(**kwargs):
    import argparse

    parser = argparse.ArgumentParser(description="icon2 node Database Backup")
    
    parser.add_argument("-p",    "--profile",       default=None)
    parser.add_argument("-r",    "--region",        type=str, help=f"Region" ,        choices=["kr", "jp", "va", "hk", "sg", "mb", "ff", "sy"], default="kr")
    parser.add_argument("-t",    "--upload_type",   type=str, help=f"upload type",    choices=["single", "multi", "sync"], default=f"{kwargs.get('upload_type')}")
    parser.add_argument("-down", "--download_type", type=str, help=f"download type",  choices=["s3", "cf", "sync"], default=f"{kwargs.get('download_type')}")

    parser.add_argument("-db",   "--db_path",     help=f"DB Path",     default=f"{kwargs.get('db_path')}" )
    parser.add_argument("-bk",   "--backup_path", help=f"Backup Path", default=f"{kwargs.get('backup_dir')}" )
    parser.add_argument("-n",    "--network",     type=str, help=f"Network name", choices=["MainNet", "TestNet"],default=f"{kwargs.get('node_network')}")
    parser.add_argument("-url",  "--send_url",    type=str, help=f"Noti Send URL", default=None)
    parser.add_argument("--is_mig_db",    type=str, help=f"Migration DB Upload", default=f"{kwargs.get('is_mig_db')}")

    return parser.parse_args()


def main():
    ### static environment 

    aws_profile = 'default'
    aws_region = 'kr'
    aws_upload_type = 'multi'      #### [ multi | sync] 
    aws_download_type = 'sync'       #### [ s3 | cf | sync ]

    db_dir = "/app/goloop/data"
    backup_dir = "/app/goloop/db_backup"
    node_network = 'MainNet_test'

    docker_path = "/app/goloop"

    indexing_in_url = f'https://icon2-backup-kr.s3.ap-northeast-2.amazonaws.com/s3sync'

    send_url = f"https://hooks.slack.com/services/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"

    ## Default : False
    icon2_is_mig_db = False
    #icon2_is_mig_db = True

    ####  사용자 argument Check 
    if len(sys.argv) > 1 :
        args = parse_args()
    else : 
        args = parse_args(db_path=db_dir, backup_dir=backup_dir, upload_type=aws_upload_type, download_type=aws_download_type, network=node_network, is_mig_db=icon2_is_mig_db)

    db_path = args.db_path if args.db_path != "None" else db_dir
    backup_path = args.backup_path if args.backup_path != 'None' else backup_dir
    upload_type = args.upload_type if args.upload_type != 'None' else aws_upload_type
    download_type = args.download_type if args.download_type != 'None' else aws_download_type
    network = args.network if args.network != 'None' else node_network
    is_mig_db = args.is_mig_db if args.is_mig_db != 'None' else icon2_is_mig_db
    
    log_print(f'++ db_path : {db_path}', "yellow")
    log_print(f'++ backup_path : {backup_path}')
    log_print(f'++ upload_type : {upload_type}')
    log_print(f'++ download_type : {download_type}')
    log_print(f'++ network : {network}')
    log_print(f'++ is_mig_db : {is_mig_db}')



    Backup(
        core_version="core2",   ### default= core2 , choice [core1] or [core2]
        profile="default",
        region=args.region,

        network=network,

        upload_type=upload_type,
        download_url_type=download_type,
        download_url=indexing_in_url,

        is_mig_db=is_mig_db,      #### Icon1 to Icon2 Migration DB Backup 

        docker_path=docker_path,
        docker_file="docker-compose.yml",
        comp_job_dir='temp',
        control_chain = True,
        db_path=db_path,
        backup_path=backup_path,
        send_url=send_url,
    )


if __name__ == "__main__":
    main()
