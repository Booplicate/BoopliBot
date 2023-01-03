"""
Modules with tests for the main bot methods
"""

import unittest
from unittest.mock import patch
import os


import discord
# import discord.ext.test as discord_test


from BoopliBot import bot
from BoopliBot.utils import config_utils


def setUpModule() -> None:
    pass

def tearDownModule() -> None:
    pass

class BotTest(unittest.TestCase):
    """
    Test case for main methods of BoopliBot.bot.Bot
    """
    CONFIG_FP = os.path.join(
        os.path.dirname(os.path.realpath(os.path.abspath(__file__))),
        "fixtures/bot_config.json"
    )

    def setUp(self) -> None:
        pass

    def tearDown(self) -> None:
        pass

    @classmethod
    def setUpClass(cls) -> None:
        pass

    @classmethod
    def tearDownClass(cls) -> None:
        pass
