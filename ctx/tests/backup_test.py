#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os

from boto3.s3.transfer import TransferConfig
from botocore.handlers import disable_signing
from timeit import default_timer

parent_dir = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
sys.path.append(parent_dir)
sys.path.append(parent_dir+"/..")

from config.configure import Configure
from common import converter, output, base

from common.output import cprint, converter

from manager import backup

print(converter.todaydate("file"))
print(converter.todaydate())

# local_dir_info = {}

# res = dict(shutil.disk_usage("/Users/jinwoo/work/ICON2_TEST"))
# print(res.usage)

# exit()

backup.Backup(
    db_path="/Users/jinwoo/work/ICON2_TEST",
    profile="upload_test",
    send_url=""
)


# res = base.run_execute("ls ----")
# output.dump(res)





