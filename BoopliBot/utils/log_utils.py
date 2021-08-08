"""
Module that handles logging
"""

import os
import sys
import logging
from logging import handlers as log_handlers
from queue import Queue


LOG_FOLDER = "logs"
MAIN_LOG_FILE = "booplibot.log"
WARNINGS_LOG_FILE = "warnings.log"

DEF_FMT = "[{asctime}] [{levelname}] [{name}]: {message}"
NONAME_FMT = "[{asctime}] [{levelname}]: {message}"
DEF_DATEFMT = "%Y-%m-%d %H:%M:%S"
F_STYLE = "{"
# These are for rotating logs
MAX_LOG_SIZE = 5*1024*1024# 5 MiB
MAX_LOG_BACKUPS = 10
EXEC_INFO = logging.INFO + 5
logging.addLevelName(EXEC_INFO, "EXECUTION")


logger: logging.Logger = None
# Writes logs in a thread
log_listener: log_handlers.QueueListener = None


def init(should_log=True) -> None:
    """
    Inits logs

    IN:
        should_log - whether or not we should log about successful init
    """
    global logger, log_listener

    # First of all, check the folder
    logs_path = os.path.join(os.getcwd(), LOG_FOLDER)
    if not os.path.exists(logs_path):
        os.mkdir(logs_path)

    # We use the same formatter for everything (almost)
    def_formatter = logging.Formatter(fmt=DEF_FMT, datefmt=DEF_DATEFMT, style=F_STYLE)

    # Console handler - warnings+
    console_handler = logging.StreamHandler(stream=sys.stdout)
    console_handler.setFormatter(def_formatter)
    console_handler.setLevel(EXEC_INFO)

    # Main log handler - info+
    main_log_handler = logging.FileHandler(
        filename=os.path.join(logs_path, MAIN_LOG_FILE),
        mode="w",
        encoding="utf-8",
        delay=True
    )
    main_log_handler.setFormatter(def_formatter)
    main_log_handler.setLevel(logging.INFO)

    # Persistent log handler - warnings+
    warnings_log_handler = log_handlers.RotatingFileHandler(
        filename=os.path.join(logs_path, WARNINGS_LOG_FILE),
        mode="a",
        maxBytes=MAX_LOG_SIZE,
        backupCount=MAX_LOG_BACKUPS,
        encoding="utf-8",
        delay=True
    )
    warnings_log_handler.setFormatter(def_formatter)
    warnings_log_handler.setLevel(logging.WARNING)

    log_queue = Queue(-1)
    # Adds log entries to the queue
    queue_handler = log_handlers.QueueHandler(log_queue)
    queue_handler.setLevel(logging.DEBUG)
    # Dispatches log entries to other handlers to actually log them
    log_listener = log_handlers.QueueListener(
        log_queue,
        console_handler,
        main_log_handler,
        warnings_log_handler,
        respect_handler_level=True
    )

    booplibot_logger = logging.getLogger("BoopliBot")
    booplibot_logger.setLevel(logging.DEBUG)
    booplibot_logger.addHandler(queue_handler)

    discordpy_logger = logging.getLogger("discord")
    discordpy_logger.setLevel(logging.DEBUG)
    discordpy_logger.addHandler(queue_handler)

    log_listener.start()

    logger = logging.getLogger(__name__)
    if should_log:
        logger.info("Logs inited.")

def deinit(should_log=True) -> None:
    """
    Deinits logs

    IN:
        should_log - whether or not we should log about successful deinit
    """
    if should_log:
        logger.info("Logs deinited.")
    log_listener.stop()

    for logger_name in ("BoopliBot", "discord"):
        logger_ = logging.getLogger(logger_name)
        for handler in logger_.handlers:
            logger_.removeHandler(handler)

        for filter_ in logger_.filters:
            logger_.removeFilter(filter_)

    logging.shutdown()
