#!/usr/bin/env python3
import os
import logging
from logging import handlers
import datetime
from rich.console import Console
from rich.logging import RichHandler


class CustomLog:
    def __init__(self, name):
        self.log = logging.getLogger(name)
        self.log.propagate = True
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

    def add_rich_handler(self, level):
        console = Console()
        logging_handler = RichHandler(console=console)
        logging_handler.setLevel(self.levels[level])
        logging_handler.setFormatter(self.formatter)
        logging_handler._log_render.show_time = False
        logging_handler._log_render.show_level = False
        logging_handler._log_render.show_path = False
        self.log.addHandler(logging_handler)
        return self.log

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
        _stream_handler = logging.StreamHandler()
        _stream_handler.setLevel(self.levels[level])
        _stream_handler.setFormatter(self.formatter)
        self.log.addHandler(_stream_handler)
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
        _file_handler = logging.FileHandler(file_name, mode=mode)
        _file_handler.setLevel(logging.DEBUG)
        _file_handler.setFormatter(self.formatter)
        self.log.addHandler(_file_handler)
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

        _file_handler = logging.handlers.RotatingFileHandler(
            filename=file_name,
            maxBytes=log_max_size,
            backupCount=backup_count,
            mode=mode)
        _file_handler.setLevel(self.levels[level])
        _file_handler.setFormatter(self.formatter)
        self.log.addHandler(_file_handler)
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
        _file_handler = logging.handlers.TimedRotatingFileHandler(
            filename=filename,
            when=when,  # W0
            backupCount=backup_count,
            interval=interval,
            atTime=atTime)
        _file_handler.setLevel(self.levels[level])
        _file_handler.setFormatter(self.formatter)
        self.log.addHandler(_file_handler)
        return self.log

    def error_file_handler(self, file_name):
        """
        오직 ERROR 레벨 로그를 위한 파일 핸들러 설정
        :param file_name: 로그 파일명 (예: 'error.log')
        :return: 로거 객체
        """
        _file_handler = logging.FileHandler(file_name, mode='a')
        _file_handler.setLevel(logging.ERROR)  # ERROR 레벨 설정
        _file_handler.setFormatter(self.formatter)
        self.log.addHandler(_file_handler)
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
