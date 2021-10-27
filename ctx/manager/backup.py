#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, os, datetime, inspect
import threading
import shutil
import argparse
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
from common.output import lineno, script_name, funcname

sys.excepthook = output.exception_handler

class Backup:
    def __init__(
        self,
        core_version="core2",
        profile="default",
        db_path=None,
        backup_path=None,
        network="MainNet",
        send_url=None,
        bucket_name_prefix="icon2-backup-",
        region="jp",
        upload_type="multi",
        ipaddr='localhost',
        docker_path="/app/goloop",
        docker_file="docker-compose.yml",
        comp_job_dir='temp',
        ):
        self.profile = profile
        self.db_path = db_path
        self.backup_path = backup_path
        self.network = network
        self.upload_filename = ""
        self.send_url = send_url
        self.bucket_name_prefix = bucket_name_prefix
        self.region = region
        self.upload_type = upload_type
        self.docker_path = docker_path
        self.docker_file = docker_file
        self.core_version = core_version
        self.ipaddr = ipaddr
        self.comp_job_dir = comp_job_dir

        if send_url:
            self.is_send = True
        else:
            self.is_send = False

        if self.db_path is None or not output.is_file(self.db_path):
            raise ValueError(f"{script_name()}({funcname()}.{lineno()}) | db_path not found - '{self.db_path}'")
        if self.backup_path is None or not output.is_file(self.backup_path):
            raise ValueError(f"{script_name()}({funcname()}.{lineno()}) | backup_path not found - '{self.backup_path}'")

        self.run()


    def run(self):
        diskcheck_per = 70

        # Backup WorkDir Create
        self.createFolder(os.path.join(self.backup_path, self.comp_job_dir))

        # Node Status Check
        self.get_loopchain_state(core_version=self.core_version, ipaddr=self.ipaddr)

        # ASIS Backup File Delete
        self.as_file_remove()

        total, used, free = shutil.disk_usage(self.backup_path)
        dirsize = self.get_dir_size(self.db_path)
        #### 남은 공간 대비 db 디렉토리 사용량 (퍼센트)
        dirusage = dirsize / free * 100.0

        if dirusage > diskcheck_per:
            self.send_slack(f"Not enough disk space : {dirusage:.2f}", "error")
            raise ValueError(f"{script_name()}({funcname()}.{lineno()}) | Not enough disk : {dirusage:.2f} %")
        else:
            output.cprint(f"++ {script_name()}({funcname()}.{lineno()}) | You have enough disk space : {self.backup_path} usage => {dirusage:.2f} %", 'yellow')

        self.run_peer(self.docker_path, self.docker_file, "stop")

        # LevelDB File Compress
        self.db_file_compress()

        self.run_peer(self.docker_path, self.docker_file, "start")

        self.upload()


    def db_file_compress(self):

        chain_id = self.cid
        os.chdir(self.db_path)

        tar_exclude_opt = ''
        tar_exclude_list = ['config.json', ]
        for exlist in tar_exclude_list:
            tar_exclude_opt += f'--exclude {exlist} '

        comp_algorithm = 'pzstd'

        tar_split_size = 100
        tar_split_opt = f'split -b {tar_split_size}m'

        if os.path.isdir(self.db_path) :
            sour_dir = os.path.join(self.backup_path, self.comp_job_dir)
            # cmd = f"tar -I pigz -cf {upload_filename} {db_dir[0]} {db_dir[1]}"
            cmd = f"tar {tar_exclude_opt} -cf - {chain_id} | {comp_algorithm} | {tar_split_opt} - {sour_dir}/{self.upload_filename}"
            output.cprint(f"++ {script_name()}({funcname()}.{lineno()}) | cmd = {cmd}" , 'yellow')

            if base.run_execute(cmd).get("stderr"):
            # if os.system(f"{cmd}") is not 0:
                self.send_slack(f"Compress Failed : {cmd}", "error")
                raise OSError(f"{script_name()}({funcname()}.{lineno()}) | Failed compression - '{cmd}'")

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


    def get_dir_size(self, path):
        total = 0
        with os.scandir(path) as it:
            for entry in it:
                if entry.is_file():
                    total += entry.stat().st_size
                elif entry.is_dir():
                    total += self.get_dir_size(entry.path)
        return total

    def as_file_remove(self):
        backup_dir = os.path.join(self.backup_path, self.comp_job_dir)
        filelist = os.listdir(f"{backup_dir}")
        for item in filelist:
            #if item.endswith(f".tar"):
            os.remove(os.path.join(backup_dir, item))
            output.cprint(f"-- {script_name()}({funcname()}.{lineno()}) | delete {backup_dir} {item}", 'red')

    # Backup WorkDir Create
    def createFolder(self, directory):
        try:
            if not os.path.exists(directory):
                os.makedirs(directory)
        except OSError:
            raise OSError("{script_name()}({funcname()}.{lineno()}) | Error: Creating directory. " + directory)


    #def get_loopchain_state(self, ipaddr="210.180.69.101", port=os.environ.get("RPC_PORT", 9000)):
    def get_loopchain_state(self, core_version='core2', ipaddr="localhost", port=os.environ.get("RPC_PORT", 9000)):
        try:
            if core_version == 'core1':
                url = f"http://{ipaddr}:{port}/api/v1/status/peer"
                r = requests.get(url, verify=False, timeout=5)
                peer_status = r.json()["status"]
            else:
                url = f"http://{ipaddr}:{port}/admin/chain"
                r = requests.get(url, verify=False, timeout=5)
                peer_status = r.json()[0]["state"]

            if peer_status == "Service is online: 0" :
                self.block_height = r.json()["block_height"]
                self.nid = r.json()['nid'].replace("0x",'')
                output.cprint(f'++ {script_name()}({funcname()}.{lineno()}) | core_version : {core_version} / nid : {self.nid} ', 'green')
            elif peer_status == "started":
                self.cid = r.json()[0]['cid'].replace("0x",'')
                self.nid = r.json()[0]['nid'].replace("0x",'')
                self.block_height = r.json()[0]["height"]
                output.cprint(f'++ {script_name()}({funcname()}.{lineno()}) | core_version : {core_version} / cid : {self.cid} / nid : {self.nid} ', 'green')

            if self.block_height:
                output.cprint(f'++ {script_name()}({funcname()}.{lineno()}) | core_version : {core_version} | Block_Height : {self.block_height}', 'green')

                self.upload_filename = (
                    f"{self.network}_BH{self.block_height}_data-{converter.todaydate('file')}.tar.zst"
                )
            else:
                error_keyword = f"Please check the peer status. : {peer_status}"

                output.cprint(error_keyword,'red')
                self.send_slack(error_keyword, "error")
                raise RuntimeError(error_keyword)
        except:
            except_keyword = f"Please check the node status. :  {url}"
            self.send_slack(except_keyword, "error")
            raise RuntimeError(except_keyword)

        return self.block_height if core_version == 'core1' else self.block_height, self.cid

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
            output.cprint(f"-- {script_name()}({funcname()}.{lineno()}) | Unknown upload_type-> {upload_type}", "red")
            raise SystemExit()

        if filename is None:
            output.cprint(f"-- {script_name()}({funcname()}.{lineno()}) | [ERROR] filename is None", "red")
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
            output.cprint(f"\n {script_name()}({funcname()}.{lineno()}) | [ERROR] File upload fail / cause -> {e}\n", "red")
            raise SystemExit()

        elapsed = default_timer() - start_time
        time_completed_at = "{:5.3f}s".format(elapsed)

        output.cprint(f"\n\t{threading.get_ident()} | {filename} |  time_completed_at = {time_completed_at}", 'green')

    def upload(self):
        cksum_dict = {}

        ### add CID info
        cksum_dict['CID'] = self.cid

        sour_dir = os.path.join(self.backup_path, self.comp_job_dir)
        dest_dir = f"{self.network}/{converter.todaydate()}/{converter.todaydate('hour')}"

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
                    output.cprint(f"\n {script_name()}({funcname()}.{lineno()}) | [ERROR] File upload fail / cause -> {e}\n", "red")

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
                pIndex_file : f"{self.network}/{pIndex_filename}"
            }

            for key, value in index_info.items():
                upload_file = key
                upload_s3_path = value
                if pIndex_filename in upload_file :
                    #s3api_cmd = f'aws s3api list-objects --bucket {self.BUCKET_NAME} --query "Contents[?contains(Key, \'{index2_filename}\')].[Key]" --output=text > {pIndex_file}'
                    s3api_cmd = f'aws s3api list-objects --bucket {self.BUCKET_NAME}'
                    s3api_query = f'--query \"Contents[?contains(Key, \'{index2_filename}\')].[Key]\" --output=text'
                    s3cmd = f'{s3api_cmd} {s3api_query} > {pIndex_file}'
                    output.cprint(f' ++ {script_name()}({funcname()}.{lineno()}) | {s3cmd}','yellow')

                    base.run_execute(s3cmd, capture_output=False)
                    output.cprint(f' ++ {script_name()}({funcname()}.{lineno()}) | pIndex_file : {pIndex_file}','yellow')

                self.multi_part_upload_with_s3(
                            upload_file,
                            upload_s3_path,
                            self.region,
                            self.upload_type
                )

            for_elapsed = default_timer() - for_start_time
            for_time_completed_at = "{:5.3f}s".format(for_elapsed)
            output.cprint(f"\n\n>>>> for_time_completed_at = {for_time_completed_at}\n", 'yellow')
        return True


    def run_peer(self, run_path, dc_file, run_mode):
        os.chdir(run_path)

        ## docker-compose config file exist check
        if os.path.isfile(os.path.join(run_path,dc_file)) is False :
            #cprint(f'--Error | Not found file :  {os.path.join(run_path,dc_file)}', 'red')
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
                output.cprint(f'-- {script_name()}({funcname()}.{lineno()}) | Not found \"{os.path.join(run_path,"docker-compose.yml")}\"', 'red')
                raise SystemExit()

        docker_cmd = 'docker-compose'
        docker_ops = f' -f {dc_file}'

        ## run mode
        run_mode = run_mode.lower()
        try :
            if run_mode == "start" or run_mode == "up" :
                run_cmd = docker_cmd + docker_ops + " up -d"
            elif run_mode == "stop" or run_mode == "down" :
                run_cmd = docker_cmd + docker_ops + " down"
            elif run_mode == "status":
                run_cmd = f'{docker_cmd} + "ps"'
            else :
                output.cprint(f'-- {script_name()}({funcname()}.{lineno()}) | Not found run_mode : {run_mode}  - [start|stop|status]', 'green')
                raise SystemExit()

            run_stat = base.run_execute(run_cmd, capture_output=False)

            return run_stat
        except :
            pass

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
