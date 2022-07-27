import logging
import logging.config
import os
import sys

def raise_exception_with_logger_info(msg):
    logger.critical(msg)
    stdout = logger.handlers[0].baseFilename
    stderr = logger.handlers[1].baseFilename
    with open(stderr, "r") as stderr_fp:
        stderr_content = stderr_fp.read()
    raise Exception(f"{msg}\nstdout = {stdout}\nstderr =\n{stderr_content}\n")

logging.config.fileConfig(fname=os.path.join(os.path.dirname(__file__), "logging.conf"), disable_existing_loggers=False)
logger = logging.getLogger("conan")
