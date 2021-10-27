#!/usr/bin/env python3
#https://hooks.slack.com/services/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
from config.configure import Configure
from common import base, output

conf = Configure()
print(conf)

res = base.run_execute("ls -al")
output.dump(res)

send_res = output.send_slack(
    url="https://hooks.slack.com/services/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",
    msg_text="test"
)

print(send_res)


