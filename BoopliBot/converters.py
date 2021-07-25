"""
Module contains argument converters.
"""

import re
from typing import (
    Union,
    Any
)


import discord
from discord.ext import commands


import BoopliBot
from . import (
    errors
)


class MemberOrUserConverter(commands.MemberConverter, commands.UserConverter):
    """
    Subclass of MemberConverter, allows to fetch members that aren't in the guild
    NOTE: in case member isn't found, fetches the user and returns it

    This is like Union[discord.Member, discord.User], but more convenient.
    """
    async def convert(self, ctx: commands.Context, argument: Any) -> Union[discord.Member, discord.User]:
        """
        Tries to conver the given argument into a Member or User objects

        IN:
            ctx - command context object
            argument - the arg to convert

        OUT:
            discord.Member OR discord.User (in this order)
        """
        try:
            return await commands.MemberConverter.convert(self, ctx, argument)

        except commands.MemberNotFound:
            try:
                return await commands.UserConverter.convert(self, ctx, argument)

            except commands.UserNotFound as unf_e:
                raise errors.MemberOrUserNotFound(argument) from unf_e

class LocalEmojiConverter(commands.EmojiConverter):
    """
    Special version of emoji converted. Searches for the emoji only in the guild where the command was invoked
    """
    async def convert(self, ctx: commands.Context, argument: Any) -> discord.Emoji:
        """
        Tries to conver the given argument into an Emoji object

        IN:
            ctx - command context object
            argument - the arg to convert

        OUT:
            discord.Emoji
        """
        match = self._get_id_match(argument) or re.match(r'<a?:[a-zA-Z0-9\_]+:([0-9]+)>$', argument)
        result = None
        guild = ctx.guild

        if match is None:
            # Try to get the emoji by name.
            if guild:
                result = discord.utils.get(guild.emojis, name=argument)

        else:
            emoji_id = int(match.group(1))

            # Try to look up emoji by id.
            if guild:
                result = discord.utils.get(guild.emojis, id=emoji_id)

        if result is None:
            raise commands.EmojiNotFound(argument)

        return result
