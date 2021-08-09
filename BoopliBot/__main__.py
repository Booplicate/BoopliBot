"""
Magic file to run the bot
"""

import os
import sys
# sys.path.append(os.getcwd())
import platform
import logging
import time
# import gc
import atexit


if __package__ is None:
    path = os.path.realpath(os.path.abspath(__file__))
    sys.path.insert(0, os.path.dirname(os.path.dirname(path)))


from . import bot, utils
from .utils import (
    log_utils,
    config_utils
)

logger: logging.Logger = None


def patch_proactor_event_loop():
    """
    HACK: Patcher for proactor event loop crash
    Original source: https://github.com/aio-libs/aiohttp/issues/4324#issuecomment-733884349
    """
    if platform.system() != "Windows":
        return False

    # import asyncio
    from functools import wraps
    from asyncio.proactor_events import _ProactorBasePipeTransport
    # asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    def silence_event_loop_closed(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except RuntimeError as e:
                if str(e) != "Event loop is closed":
                    raise
        return wrapper

    setattr(
        _ProactorBasePipeTransport,
        "__del__",
        silence_event_loop_closed(_ProactorBasePipeTransport.__del__)
    )
    return True

def main() -> None:
    """
    Main point of the program

    NOTE: RETURNS EXIT CODES:
        0 FOR EXIT
        1 FOR RESTART AFTER CRASH
        65 FOR PLANNED RESTART
    """
    global logger

    patch_proactor_event_loop()

    atexit.register(utils.deinit)
    utils.init()

    logger = logging.getLogger("BoopliBot")
    config = config_utils.bot_config

    try:
        booplibot = bot.Bot(config)

        logger.log(log_utils.EXEC_INFO, "Starting BoopliBot.")
        booplibot.run(config.token, bot=True, reconnect=True)

    except Exception as e:
        logger.error("Got exception during the main loop.", exc_info=e)
        time.sleep(5)

    finally:
        exit_code = booplibot.exit_code

        if exit_code == bot.Bot.EXIT_CODE_QUIT:
            logger.log(log_utils.EXEC_INFO, "Shutting down BoopliBot.")

        elif exit_code == bot.Bot.EXIT_CODE_CRASH:
            logger.log(log_utils.EXEC_INFO, "Restarting BoopliBot (after crash).")

        elif exit_code == bot.Bot.EXIT_CODE_RESTART:
            logger.log(log_utils.EXEC_INFO, "Restarting BoopliBot (planned).")

        else:
            # raise Exception(f"UNKNOWN EXIT CODE: '{exit_code}'.")
            logger.error(f"Unknown exit code '{exit_code}'. Shutting down BoopliBot.")
            exit_code = bot.Bot.EXIT_CODE_QUIT

        sys.exit(exit_code)


if __name__ == "__main__":
    main()
