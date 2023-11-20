#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import append_parent_path
from manager.ntp import NTPDaemon
from common.runner import AsyncRunner
import os
from pawnlib.config import pawn

from manager.chain_init import ChainInit
CI = ChainInit()
CI.set_system_config()
