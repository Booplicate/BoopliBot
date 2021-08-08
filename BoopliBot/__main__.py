"""
Magic file to run the bot
"""

import os
import sys
# sys.path.append(os.getcwd())
# import asyncio
# import platform
import logging
import time
# import gc


if __package__ is None:
    path = os.path.realpath(os.path.abspath(__file__))
    sys.path.insert(0, os.path.dirname(os.path.dirname(path)))
# print(sys.path)


from . import bot, utils
from .utils import (
    log_utils,
    config_utils,
    # sql_utils
)

logger: logging.Logger = None


def main() -> None:
    """
    Main point of the program

    NOTE: RETURNS EXIT CODE 0 FOR EXIT AND 130 FOR RESTART REQUEST
    """
    global logger

    utils.init()

    # Windows needs a different event loop
    # if platform.system() == "Windows":
    #     asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    logger = logging.getLogger("BoopliBot")

    config = config_utils.bot_config
    booplibot = bot.Bot(config)

    try:
        logger.log(log_utils.EXEC_INFO, "Starting BoopliBot.")
        booplibot.run(config.token, bot=True, reconnect=True)

    except Exception as e:
        logger.error("Got exception during the loop.", exc_info=e)
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
            raise Exception(f"UNKNOWN EXIT CODE: '{exit_code}'.")

        utils.deinit()

        sys.exit(exit_code)


if __name__ == "__main__":
    main()
