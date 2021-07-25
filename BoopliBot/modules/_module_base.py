"""
This is a base for implementing future modules.
"""


from typing import (
    Any
)

import discord
from discord.ext import commands


import BoopliBot
from .. import (
    bot
)
from ..utils import (
    register_cog
)


_cogs = set()


@register_cog(_cogs)
class BaseModule(commands.Cog):
    """
    Logger contains methods for chat logs handling
    """
    def __init__(self, bot: bot.Bot):
        """
        Constructor

        IN:
            bot - the bot object
        """
        self.bot = bot


def setup(bot: bot.Bot):
    for cog in _cogs:
        bot.add_cog(cog(bot))

def teardown(bot: bot.Bot):
    for cog in _cogs:
        bot.remove_cog(cog(bot))
