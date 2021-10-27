#!/usr/bin/env python3
import os
import logging
from logging import handlers
import datetime

class CustomLog:
    def __init__(self, name):
        self.log = logging.getLogger(name)
        self.log.propagate = True
        # self.formatter = logging.Formatter("%(levelname).1s|%(asctime)s.%(msecs)06d|-|%(name)s|%(message)s", "%Y%m%d-%H:%M:%S")
        # self.formatter = logging.Formatter(f"%(levelname).1s|%(asctime)s.%(msecs)06d|-|%(name)s|%(filename)s:%(lineno)d %(funcName)-15s| %(message)s", "%Y%m%d-%H:%M:%S")
        self.formatter = logging.Formatter(
            f"%(levelname).1s|%(asctime)s.%(msecs)06d|-|%(name)s|%(filename)s:%(lineno)d| %(message)s",
            "%Y%m%d-%H:%M:%S"
        )
        self.levels = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL}


    def set_level(self, level):
        self.log.setLevel(self.levels[level])

    def log_formatter(self, msg):
        """
        :return:
        """
        log_str = f"{msg}"
        return log_str

    def stream_handler(self, level):
        """
        :param level:
        > "DEBUG" : logging.DEBUG ,
        > "INFO" : logging.INFO ,
        > "WARNING" : logging.WARNING ,
        > "ERROR" : logging.ERROR ,
        > "CRITICAL" : logging.CRITICAL ,
        :return:
        """
        streamHandler = logging.StreamHandler()
        streamHandler.setLevel(self.levels[level])
        streamHandler.setFormatter(self.formatter)
        self.log.addHandler(streamHandler)
        return self.log

    def file_handler(self, file_name, mode):
        """
        :param file_name: ~.txt / ~.log
        :param mode: "w" / "a"
        > "DEBUG" : logging.DEBUG ,
        > "INFO" : logging.INFO ,
        > "WARNING" : logging.WARNING ,
        > "ERROR" : logging.ERROR ,
        > "CRITICAL" : logging.CRITICAL ,
        :return:
        """
        fileHandler = logging.FileHandler(file_name, mode=mode)
        fileHandler.setLevel(logging.DEBUG)
        fileHandler.setFormatter(self.formatter)
        self.log.addHandler(fileHandler)
        return self.log

    def file_rotating_handler(self, file_name, mode, level, backup_count, log_max_size):
        """
        :param file_name: ~.txt / ~.log
        :param mode: "w" / "a"
        :param backup_count: backup할 파일 개수
        :param log_max_size: 한 파일당 용량 최대
        :param level:
        > "DEBUG" : logging.DEBUG ,
        > "INFO" : logging.INFO ,
        > "WARNING" : logging.WARNING ,
        > "ERROR" : logging.ERROR ,
        > "CRITICAL" : logging.CRITICAL ,
        :return:
        """

        fileHandler = logging.handlers.RotatingFileHandler(
            filename=file_name,
            maxBytes=log_max_size,
            backupCount=backup_count,
            mode=mode)
        fileHandler.setLevel(self.levels[level])
        fileHandler.setFormatter(self.formatter)
        self.log.addHandler(fileHandler)
        return self.log

    def time_rotate_handler(self,
                           filename='./log.txt',
                           when="M",
                           level="DEBUG",
                           backup_count=4,
                           atTime=datetime.time(0, 0, 0),
                           interval=1):
        """
        :param filename:
        :param when: 저장 주기
        :param interval: 저장 주기에서 어떤 간격으로 저장할지
        :param backup_count: 5
        :param atTime: datetime.time(0, 0, 0)
        :return:
        """
        fileHandler = logging.handlers.TimedRotatingFileHandler(
            filename=filename,
            when=when,  # W0
            backupCount=backup_count,
            interval=interval,
            atTime=atTime)
        fileHandler.setLevel(self.levels[level])
        fileHandler.setFormatter(self.formatter)
        self.log.addHandler(fileHandler)
        return self.log


if __name__ == '__main__':
    from time import sleep
    file_name = './time_log.txt'
    logger = CustomLog("custom_log")
    logger.set_level('DEBUG')
    logger.stream_handler("INFO")
    logger.time_rotate_handler(filename=file_name,
                                 when="M",
                                 interval=2,
                                 backup_count=3,
                                 level="INFO"
                                 )
    ## run
    idx = 0
    while True:
        logger.log.debug(logger.log_formatter(f'debug {idx}'))
        logger.log.info(logger.log_formatter(f'info {idx}'))
        logger.log.warning(logger.log_formatter(f'warning {idx}'))
        logger.log.error(logger.log_formatter(f'error {idx}'))
        logger.log.critical(logger.log_formatter(f'critical {idx}'))
        idx += 1
        sleep(0.5)
        if idx == 1000:
            break
