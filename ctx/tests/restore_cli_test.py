#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pawnlib.config import pawn
import append_parent_path
from config.configure import Configure
from common import output, base
from manager.restore_v3 import Restore



def main():
    base.disable_ssl_warnings()
    cfg = Configure()
    output.dump(cfg.config)
    print(cfg.config['DOWNLOAD_URL'])
    restore = Restore(
        db_path=cfg.config['GOLOOP_NODE_DIR'],
        network=cfg.config['SERVICE'],
        download_path=cfg.config['RESTORE_PATH'],
        download_force=cfg.config['DOWNLOAD_FORCE'],
        download_url=cfg.config['DOWNLOAD_URL'],
        download_url_type=cfg.config['DOWNLOAD_URL_TYPE'],
        download_option=cfg.config.get('DOWNLOAD_OPTION', None),
        # download_tool=download_tool,
    )
    # restore.run()
    restore._prepare()
    restore.check_downloaded_file()
    restore.create_db_redownload_list()

if __name__ == "__main__":
    main()
