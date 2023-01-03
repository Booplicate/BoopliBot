"""
Module provides set of commands to work with roles.
"""

from typing import (
    Optional
)

import discord
from discord.ext import commands


import BoopliBot
from ..bot import Bot
from ..utils import register_cog
from ..errors import (
    MissingRequiredSubCommand
)
from ..converters import MemberOrUserConverter


_cogs = set()


@register_cog(_cogs)
class RoleCommands(commands.Cog, name="Roles Management"):
    """
    This collection provides commands for managementing roles
    """
    def __init__(self, bot: Bot):
        """
        Constructor

        IN:
            bot - the bot object
        """
        self.bot = bot

    @commands.group(name="role", invoke_without_command=True)
    async def cmd_role(self, ctx: commands.Context) -> None:
        """
        Group of commands to manage roles
        """
        if ctx.invoked_subcommand is None:
            raise MissingRequiredSubCommand()

    @cmd_role.command(name="add", aliases=("grant",))
    async def cmd_role_add(self, ctx: commands.Context, role: discord.Role, user: Optional[discord.Member] = None) -> None:
        """
        Adds the role to a member

        IN:
            role - the role to give
            user - the user who will receive the role (optional, default - you)
        """
        if user is None:
            user = ctx.author

        role_name = discord.utils.escape_mentions(role.name)

        if role in user.roles:
            if user == ctx.author:
                msg = f"You already have the role **{role_name}**."

            else:
                msg = f"The user {user.mention} already has the role **{role_name}**."

        else:
            if user == ctx.author:
                msg = f"Added the role **{role_name}** to you."

            else:
                msg = f"Added the role **{role_name}** to {user.mention}."

            try:
                await user.add_roles(role)

            except discord.Forbidden:
                msg = f"Forbidden. The role **{role_name}** is managed by Discord."

        await ctx.send(msg, reference=ctx.message)

    @cmd_role.command(name="remove", aliases=("rm",))
    async def cmd_role_remove(self, ctx: commands.Context, role: discord.Role, user: Optional[discord.Member] = None) -> None:
        """
        Removes the role from a member

        IN:
            role - the role to remove
            user - the user who will receive the role (optional, default - you)
        """
        if user is None:
            user = ctx.author

        role_name = discord.utils.escape_mentions(role.name)

        if role not in user.roles:
            if user == ctx.author:
                msg = f"You have no role **{role_name}**."

            else:
                msg = f"The user {user.mention} has no role **{role_name}**."

        else:
            if user == ctx.author:
                msg = f"Removed the role **{role_name}** from you."

            else:
                msg = f"Removed the role **{role_name}** from {user.mention}."

            try:
                await user.remove_roles(role)

            except discord.Forbidden:
                msg = f"Forbidden. The role **{role_name}** is managed by Discord."

        await ctx.send(msg, reference=ctx.message)


def setup(bot: Bot):
    for cog in _cogs:
        bot.add_cog(cog(bot))

def teardown(bot: Bot):
    for cog in _cogs:
        bot.remove_cog(cog(bot))
