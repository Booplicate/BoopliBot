"""
This is a base for implementing future modules.
"""


from typing import (
    Any
)

import discord
from discord.ext import commands


import BoopliBot
from ..bot import Bot
from ..utils import (
    register_cog
)


_cogs = set()


@register_cog(_cogs)
class BaseModule(commands.Cog):
    """
    Base for modules
    """
    def __init__(self, bot: Bot):
        """
        Constructor

        IN:
            bot - the bot object
        """
        self.bot = bot


def setup(bot: Bot):
    for cog in _cogs:
        bot.add_cog(cog(bot))

def teardown(bot: Bot):
    for cog in _cogs:
        bot.remove_cog(cog(bot))
