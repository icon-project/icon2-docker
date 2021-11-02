#!/usr/bin/env python3
#https://hooks.slack.com/services/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
import time

from config.configure import Configure
from common import base, output

conf = Configure()
print(conf)

res = base.run_execute("ls -al")
output.dump(res)

send_res = output.send_slack(
    url="WEBHOOK_URL",
    msg_text="test"
)

print(send_res)

while True:
    time.sleep(2)
    print("---- ")
