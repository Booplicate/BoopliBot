"""
Module provides set of commands to work with emotes.
"""

from typing import (
    List
)

import discord
from discord.ext import commands


import BoopliBot
from ..utils import (
    register_cog
)
from ..bot import Bot
from ..errors import (
    MissingRequiredSubCommand,
    BadRole
)
from ..converters import LocalEmojiConverter


_cogs = set()


@register_cog(_cogs)
class EmojiCommands(commands.Cog, name="Emoji Management"):
    """
    This collection provides commands for emoji management for BoopliBot
    """
    def __init__(self, bot: Bot):
        """
        Constructor

        IN:
            bot - the bot object
        """
        self.bot = bot

    @commands.group(name="emoji", aliases=("emote",), invoke_without_command=True)
    @commands.has_guild_permissions(manage_emojis=True)
    @commands.bot_has_guild_permissions(manage_emojis=True)
    @commands.guild_only()
    async def cmd_emoji(self, ctx: commands.Context) -> None:
        """
        Group of commands to manage emojis
        """
        if ctx.invoked_subcommand is None:
            raise MissingRequiredSubCommand()

    @staticmethod
    def __fmt_emoji_roles(emoji: discord.Emoji, required_roles: List[discord.Role] = None) -> str:
        """
        TODO: sanity checks for msg len
        """
        if required_roles:
            required_roles = ", ".join(
                [
                    f"**{discord.utils.escape_mentions(role.name)}**"
                    for role in required_roles
                ]
            )

        else:
            required_roles = "everyone"

        msg = f"Emote {emoji} is available to: {required_roles}."

        return msg

    @cmd_emoji.command(name="addroles", aliases=("addrole",))
    @commands.has_guild_permissions(manage_emojis=True)
    @commands.bot_has_guild_permissions(manage_emojis=True)
    @commands.guild_only()
    async def cmd_emoji_addroles(self, ctx: commands.Context, emoji: LocalEmojiConverter, roles_to_add: commands.Greedy[discord.Role]) -> None:
        """
        """
        if emoji.guild_id != ctx.guild.id:
            raise commands.EmojiNotFound(emoji.name)

        # Verify we have a role to add
        if not roles_to_add:
            # TODO: better converted that will raise this for us
            arg = self.bot.get_command("emoji addroles").params["roles_to_add"]
            raise commands.MissingRequiredArgument(arg)

        # Fitler the @everyone role
        for role in roles_to_add:
            if role.is_default():
                raise BadRole(role)

        required_roles = emoji.roles + roles_to_add
        await emoji.edit(roles=required_roles)

        msg = EmojiCommands.__fmt_emoji_roles(emoji, required_roles=required_roles)
        await ctx.send(msg, reference=ctx.message)

    @cmd_emoji.command(name="removeroles", aliases=("removerole", "rmroles", "rmrole"))
    @commands.has_guild_permissions(manage_emojis=True)
    @commands.bot_has_guild_permissions(manage_emojis=True)
    @commands.guild_only()
    async def cmd_emoji_removeroles(self, ctx: commands.Context, emoji: LocalEmojiConverter, roles_to_remove: commands.Greedy[discord.Role]) -> None:
        """
        """
        if emoji.guild_id != ctx.guild.id:
            raise commands.EmojiNotFound(emoji.name)

        # Verify we have a role to remove
        if not roles_to_remove:
            arg = self.bot.get_command("emoji removeroles").params["roles_to_remove"]
            raise commands.MissingRequiredArgument(arg)

        required_roles = list(set(emoji.roles).difference(roles_to_remove))
        await emoji.edit(roles=required_roles)

        msg = EmojiCommands.__fmt_emoji_roles(emoji, required_roles=required_roles)
        await ctx.send(msg, reference=ctx.message)

    @cmd_emoji.command(name="setroles", aliases=("setrole",))
    @commands.has_guild_permissions(manage_emojis=True)
    @commands.bot_has_guild_permissions(manage_emojis=True)
    @commands.guild_only()
    async def cmd_emoji_setroles(self, ctx: commands.Context, emoji: LocalEmojiConverter, required_roles: commands.Greedy[discord.Role] = None) -> None:
        """
        Sets roles that can use this emoji

        IN:
            emoji - the emoji
            required_roles - the roles
        """
        if emoji.guild_id != ctx.guild.id:
            raise commands.EmojiNotFound(emoji.name)

        # Fitler the @everyone role
        if required_roles:
            for role in required_roles:
                if role.is_default():
                    raise BadRole(role)

        await emoji.edit(roles=required_roles)

        msg = EmojiCommands.__fmt_emoji_roles(emoji, required_roles=required_roles)
        await ctx.send(msg, reference=ctx.message)

    @cmd_emoji.command(name="getroles", aliases=("getrole", "parameters", "params"))
    @commands.has_guild_permissions(manage_emojis=True)
    @commands.bot_has_guild_permissions(manage_emojis=True)
    @commands.guild_only()
    async def cmd_emoji_getroles(self, ctx: commands.Context, emoji: LocalEmojiConverter = None) -> None:
        """
        Returns the roles that can use this emoji

        IN:
            emoji - the emoji (if not passed, dumps every emoji)
        """
        if emoji is None:
            guild_emojis = ctx.guild.emojis
            if not guild_emojis:
                await ctx.send("This server does not have custom emotes.", reference=ctx.message)
                return

            static_emojis = list()
            anim_emojis = list()
            for e in guild_emojis:
                required_roles = e.roles
                if not required_roles:
                    continue

                required_roles = ", ".join([f"**{role.name}**" for role in required_roles])

                line = f"{e}: {required_roles}"

                if e.animated:
                    anim_emojis.append(line)

                else:
                    static_emojis.append(line)

            if static_emojis or anim_emojis:
                embed = discord.Embed(title="Emote settings")

                if static_emojis:
                    embed.add_field(
                        name="Static emotes:",
                        value="\n".join(static_emojis),
                        inline=False
                    )

                if anim_emojis:
                    embed.add_field(
                        name="Animated emotes:",
                        value="\n".join(anim_emojis),
                        inline=False
                    )

                await ctx.send(embed=embed, reference=ctx.message)

            else:
                await ctx.send("All emotes are avaliable to everyone.", reference=ctx.message)

        else:
            if emoji.guild_id != ctx.guild.id:
                raise commands.EmojiNotFound(emoji.name)

            msg = EmojiCommands.__fmt_emoji_roles(emoji, required_roles=emoji.roles)
            await ctx.send(msg, reference=ctx.message)


def setup(bot: Bot):
    for cog in _cogs:
        bot.add_cog(cog(bot))

def teardown(bot: Bot):
    for cog in _cogs:
        bot.remove_cog(cog(bot))
