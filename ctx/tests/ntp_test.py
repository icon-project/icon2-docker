#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import append_parent_path
from manager.ntp import NTPDaemon
from common.runner import AsyncRunner
import os
from pawnlib.config import pawn

past_date = '2002-08-06'
pawn.console.log(f"To run the test, time is forcibly set to the past.  {past_date}")
os.system(f"date -s '{past_date}'")

nd = NTPDaemon(sleep_unit="seconds",)

async_runner = AsyncRunner()
async_runner.push(nd.sync_time())
async_runner.run()
