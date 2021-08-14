"""
Module contains set of ungrouped commands.
"""

import random
from typing import (
    Optional
)


import discord
from discord.ext import commands


import BoopliBot
from ..bot import Bot
from ..utils import (
    register_cog,
    is_mod_or_used_on_self,
    bypass_for_mod_cooldown,
    fmt_datetime,
    sql_utils
)
from ..converters import MemberOrUserConverter
from ..consts import (
    BOOPLIBOT_GITHUB,
    BOOPLIBOT_DEF_PREMISSIONS
)


_cogs = set()


@register_cog(_cogs)
class OtherCommands(commands.Cog, name="Other"):
    """
    This collection provides commands that don't fit in any special category
    """
    SUDO_CMD_RESPONSES = [
        "Who do you think you are?",
        "What do you think you're doing?",
        "I can't let that happen.",
        "I don't like where you're going with your commands.",
        "`sudo` your mom."
    ]

    def __init__(self, bot: Bot):
        """
        Constructor

        IN:
            bot - the bot object
        """
        self.bot = bot

    @commands.command(name="sudo", hidden=True)
    @commands.cooldown(rate=1, per=5, type=commands.cooldowns.BucketType.user)
    async def cmd_sudo(self, ctx: commands.Context, command: Optional[str] = None) -> None:
        await ctx.send(random.choice(OtherCommands.SUDO_CMD_RESPONSES))

    @commands.command(name="about")
    @commands.cooldown(rate=1, per=15, type=commands.cooldowns.BucketType.guild)
    async def cmd_about(self, ctx: commands.Context) -> None:
        """
        Shows info about this bot
        """
        info = await self.bot.application_info()
        invite_url = discord.utils.oauth_url(info.id, permissions=BOOPLIBOT_DEF_PREMISSIONS)

        embed = (
            discord.Embed(title="About me")
            .set_thumbnail(url=info.icon.url)
            .add_field(
                name="Name:",
                value=info.name,
                inline=False
            )
            .add_field(
                name="Description:",
                value=info.description,
                inline=False
            )
            .add_field(
                name="Author:",
                value=info.owner.mention,
                inline=False
            )
            .add_field(
                name="Links:",
                value=f" - [Invite me!]({invite_url})\n - [Check out my GitHub!]({BOOPLIBOT_GITHUB})",
                inline=False
            )
            .set_footer(text=f"v{BoopliBot.__version__}")
        )

        await ctx.send(embed=embed)

    @commands.command(name="who", aliases=("whois", "info"))
    @commands.guild_only()
    @commands.dynamic_cooldown(bypass_for_mod_cooldown(rate=1, per=5), type=commands.cooldowns.BucketType.user)
    async def cmd_who(self, ctx: commands.Context, *, member: MemberOrUserConverter) -> None:
        """
        Returns information about a server member/discord user

        IN:
            member - the member to fetch info for
        """
        # Can only be used on oneself or when have the permission
        is_mod_or_used_on_self(ctx.author, member)

        guild_id = ctx.guild.id
        user_id = member.id
        current_warns = total_warns = total_kicks = total_bans = 0
        async with sql_utils.NewAsyncSession() as sesh:
            sesh: sql_utils.AsyncSession

            user_data = await sesh.get(sql_utils.User, (guild_id, user_id))

            if user_data is not None:
                current_warns = user_data.current_warns
                total_warns = user_data.total_warns
                total_kicks = user_data.total_kicks
                total_bans = user_data.total_bans

        username = member.name
        discriminator = member.discriminator
        ava_url = member.avatar.url
        created_at = fmt_datetime(member.created_at)

        # If it's not a member, then we can't get the complete info
        if isinstance(member, discord.Member):
            nickname = member.nick or username
            joined_at = fmt_datetime(member.joined_at)
            premium_since = member.premium_since
            if premium_since is not None:
                premium_since = fmt_datetime(premium_since)
            roles = ", ".join([role.mention for role in reversed(member.roles)])

        else:
            nickname = username
            joined_at = "Not a member"
            premium_since = None
            roles = None

        embed = (
            discord.Embed(title=f"User info: {username}:{discriminator}")
            .set_thumbnail(url=ava_url)
            .add_field(name="Nickname:", value=nickname, inline=False)
            .add_field(name="User ID:", value=user_id, inline=False)
            .add_field(name="Created at:", value=created_at, inline=False)
            .add_field(name="Joined at:", value=joined_at, inline=False)
        )

        if premium_since is not None:
            embed.add_field(name="Booster since:", value=premium_since, inline=False)

        if roles is not None:
            embed.add_field(name="Roles:", value=roles, inline=False)

        embed.add_field(
            name="This server stats:",
            value=f"Current warnings: {current_warns}\nTimes warned: {total_warns}\nTimes kicked: {total_kicks}\nTimes banned: {total_bans}",
            inline=False
        )

        await ctx.send(embed=embed)

    @commands.command(name="getpfp", aliases=("getavatar", "getava"))
    @commands.cooldown(rate=1, per=5, type=commands.cooldowns.BucketType.user)
    async def cmd_getpfp(self, ctx: commands.Context, member: MemberOrUserConverter) -> None:
        """
        Returns user's pfp

        IN:
            member - the member whos avatar to return
        """
        await ctx.send(member.avatar.url)

    @commands.command(name="coin", aliases=("flip", "toss"))
    @commands.cooldown(rate=1, per=5, type=commands.cooldowns.BucketType.user)
    async def cmd_coin(self, ctx: commands.Context) -> None:
        """
        Flips a coin
        """
        result = random.choice(("heads", "tails"))
        await ctx.send(f"**{result.capitalize()}!**")

    @commands.command(name="choice", aliases=("select",))
    @commands.cooldown(rate=1, per=5, type=commands.cooldowns.BucketType.user)
    async def cmd_choice(self, ctx: commands.Context, *choices: str) -> None:
        """
        Selects one item from a list

        IN:
            choices - list of strings to choice from
        """
        if choices:
            result = f"**{random.choice(choices)}**"

        else:
            used_cmd = ctx.invoked_with
            result = f"Nothing to `{used_cmd}` from."

        await ctx.send(result)


def setup(bot: Bot):
    for cog in _cogs:
        bot.add_cog(cog(bot))

def teardown(bot: Bot):
    for cog in _cogs:
        bot.remove_cog(cog(bot))
