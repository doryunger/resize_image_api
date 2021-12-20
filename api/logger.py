import logging
import os


def init_logger(log_file, name='', level=logging.DEBUG):
    format = logging.Formatter('%(asctime)s [%(levelname)-7s][ln-%(lineno)-3d]: %(message)s')
    handler = logging.FileHandler(log_file, mode='w')
    handler.setFormatter(format)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    return logger