"""
Module provides set of commands to work with guild members.
"""

from typing import (
    Optional
)


import discord
from discord.ext import commands


import BoopliBot
from ..bot import Bot
from ..utils import (
    register_cog,
    sql_utils
)
from ..errors import (
    TooLowInHierarchy,
    BotTooLowInHierarchy,
    MissingRequiredSubCommand
)
from ..converters import MemberOrUserConverter
from ..helpers import PartialAuditLogEntry


_cogs = set()

MSG_WARNED = "You were warned in **{guild}**. You have **{warnings}** warning(s) now."
MSG_WARNED_WITH_REASON = "You were warned in **{guild}** with the reason: **{reason}**. You have **{warnings}** warning(s) now."
RESPONSE_WARNED = "Warned {member}. They have **{warnings}** warning(s) now."
RESPONSE_WARNED_WITH_REASON = "Warned {member} with the reason: **{reason}**. They have **{warnings}** warning(s) now."

MSG_UNWARNED = "You were forgiven one warning in **{guild}**. You have **{warnings}** warning(s) now."
MSG_UNWARNED_WITH_REASON = "You were forgiven one warning in **{guild}** with the reason: **{reason}**. You have **{warnings}** warning(s) now."
RESPONSE_UNWARNED = "Removed a warning from {member}. They have **{warnings}** warning(s) now."
RESPONSE_UNWARNED_WITH_REASON = "Removed a warning from {member} with the reason: **{reason}**. They have **{warnings}** warning(s) now."
RESPONSE_NOWARNS = "{member} has no warnings to remove."

MSG_KICKED = "You were kicked from **{guild}**."
MSG_KICKED_WITH_REASON = "You were kicked from **{guild}** with the reason: **{reason}**."
RESPONSE_KICKED = "Kicked {member}."
RESPONSE_KICKED_WITH_REASON = "Kicked {member} with the reason: **{reason}**."

MSG_BANNED = "You were banned from **{guild}**."
MSG_BANNED_WITH_REASON = "You were banned from **{guild}** with the reason: **{reason}**."
RESPONSE_BANNED = "Banned {member}."
RESPONSE_BANNED_WITH_REASON = "Banned {member} with the reason: **{reason}**."

MSG_UNBANNED = "You were unbanned in **{guild}**."
MSG_UNBANNED_WITH_REASON = "You were unbanned in **{guild}** with the reason: **{reason}**."
RESPONSE_UNBANNED = "Unbanned {member}."
RESPONSE_UNBANNED_WITH_REASON = "Unbanned {member} with the reason: **{reason}**."
RESPONSE_NOBAN = "{member} has not been banned."

ATTENTION_NO_DM = " \n**Attention**: I could not message them."


@register_cog(_cogs)
class MemberCommands(commands.Cog, name="Administration"):
    """
    This collection provides commands for managementing server members
    """
    def __init__(self, bot: Bot):
        """
        Constructor

        IN:
            bot - the bot object
        """
        self.bot = bot

    @commands.command(name="warn")
    @commands.has_guild_permissions(kick_members=True)
    @commands.guild_only()
    async def cmd_warn(self, ctx: commands.Context, member: MemberOrUserConverter, *, reason: Optional[str] = None) -> None:
        """
        Gives a warning to a server member/discord user

        IN:
            member - the member to give the warning to
            reason - the reason
        """
        guild_id = ctx.guild.id
        user_id = member.id
        warnings = 1
        async with sql_utils.NewAsyncSession() as sesh:
            sesh: sql_utils.AsyncSession

            user_data = await sesh.get(sql_utils.User, (guild_id, user_id))

            if user_data is not None:
                warnings = user_data.current_warns + 1

        if reason:
            msg_warned = MSG_WARNED_WITH_REASON.format(guild=ctx.guild.name, reason=reason, warnings=warnings)
            response_warned = RESPONSE_WARNED_WITH_REASON.format(member=member.mention, reason=reason, warnings=warnings)

        else:
            msg_warned = MSG_WARNED.format(guild=ctx.guild.name, warnings=warnings)
            response_warned = RESPONSE_WARNED.format(member=member.mention, warnings=warnings)

        # After we got the current warnings, we can dispatch
        self.bot.dispatch(
            "member_warn",
            ctx.guild,
            member,
            PartialAuditLogEntry("warn", ctx.author, member, reason)
        )

        # Sadly bots can't DM each other
        if not member.bot:
            # The user may not accept DMs, in this case we get 403
            try:
                await member.send(msg_warned)

            except discord.Forbidden:
                response_warned += ATTENTION_NO_DM

        await ctx.send(response_warned, reference=ctx.message)

    @commands.command(name="unwarn")
    @commands.has_guild_permissions(kick_members=True)
    @commands.guild_only()
    async def cmd_unwarn(self, ctx: commands.Context, member: MemberOrUserConverter, *, reason: Optional[str] = None) -> None:
        """
        Removes a warning from a server member/discord user

        IN:
            member - the member to remove the warning from
            reason - the reason
        """
        guild_id = ctx.guild.id
        user_id = member.id
        warnings = None
        async with sql_utils.NewAsyncSession() as sesh:
            sesh: sql_utils.AsyncSession

            user_data = await sesh.get(sql_utils.User, (guild_id, user_id))

            if user_data is not None and user_data.current_warns > 0:
                warnings = user_data.current_warns - 1

        # Non-None means we remove a warning
        if warnings is not None:
            if reason:
                msg_unwarned = MSG_UNWARNED_WITH_REASON.format(guild=ctx.guild.name, reason=reason, warnings=warnings)
                response_unwarned = RESPONSE_UNWARNED_WITH_REASON.format(member=member.mention, reason=reason, warnings=warnings)

            else:
                msg_unwarned = MSG_UNWARNED.format(guild=ctx.guild.name, warnings=warnings)
                response_unwarned = RESPONSE_UNWARNED.format(member=member.mention, warnings=warnings)

            if not member.bot:
                try:
                    await member.send(msg_unwarned)

                except discord.Forbidden:
                    response_unwarned += ATTENTION_NO_DM

            # Only dispatch if everything is correct
            self.bot.dispatch(
                "member_unwarn",
                ctx.guild,
                member,
                PartialAuditLogEntry("unwarn", ctx.author, member, reason)
            )

        else:
            response_unwarned = RESPONSE_NOWARNS.format(member=member.mention)

        await ctx.send(response_unwarned, reference=ctx.message)

    @commands.command(name="kick")
    @commands.has_guild_permissions(kick_members=True)
    @commands.bot_has_guild_permissions(kick_members=True)
    @commands.guild_only()
    async def cmd_kick(self, ctx: commands.Context, member: discord.Member, *, reason: Optional[str] = None) -> None:
        """
        Kicks a server member

        IN:
            member - the member to kick
            reason - the kick reason
        """
        # You must be > the target to kick/ban them, but can still do it to yourself
        # Because why not
        if ctx.author != member and ctx.author.top_role <= member.top_role:
            raise TooLowInHierarchy()

        if ctx.guild.me.top_role <= member.top_role:
            raise BotTooLowInHierarchy()

        if reason:
            msg_kicked = MSG_KICKED_WITH_REASON.format(guild=ctx.guild.name, reason=reason)
            response_kicked = RESPONSE_KICKED_WITH_REASON.format(member=member.mention, reason=reason)

        else:
            msg_kicked = MSG_KICKED.format(guild=ctx.guild.name)
            response_kicked = RESPONSE_KICKED.format(member=member.mention)

        if not member.bot:
            try:
                await member.send(msg_kicked)

            except discord.Forbidden:
                response_kicked += ATTENTION_NO_DM

        await member.kick(reason=reason)
        await ctx.send(response_kicked, reference=ctx.message)

    @commands.command(name="ban")
    @commands.has_guild_permissions(ban_members=True)
    @commands.bot_has_guild_permissions(ban_members=True)
    @commands.guild_only()
    async def cmd_ban(self, ctx: commands.Context, member: MemberOrUserConverter, *, reason: Optional[str] = None) -> None:
        """
        Bans a server member/discord user

        IN:
            member - the member to ban
            reason - the ban reason
        """
        # Instance check because non-members don't have roles
        if isinstance(member, discord.Member):
            if ctx.author != member and ctx.author.top_role <= member.top_role:
                raise TooLowInHierarchy()

            if ctx.guild.me.top_role <= member.top_role:
                raise BotTooLowInHierarchy()

        if reason:
            msg_banned = MSG_BANNED_WITH_REASON.format(guild=ctx.guild.name, reason=reason)
            response_banned = RESPONSE_BANNED_WITH_REASON.format(member=member.mention, reason=reason)

        else:
            msg_banned = MSG_BANNED.format(guild=ctx.guild.name)
            response_banned = RESPONSE_BANNED.format(member=member.mention)

        if not member.bot:
            try:
                await member.send(msg_banned)

            except discord.Forbidden:
                response_banned += ATTENTION_NO_DM

        # NOTE: we're banning through the guild because member may be either discord.Member OR discord.User
        await ctx.guild.ban(member, reason=reason, delete_message_days=0)
        await ctx.send(response_banned, reference=ctx.message)

    @commands.command(name="unban")
    @commands.has_guild_permissions(ban_members=True)
    @commands.bot_has_guild_permissions(ban_members=True)
    @commands.guild_only()
    async def cmd_unban(self, ctx: commands.Context, member: MemberOrUserConverter, *, reason: Optional[str] = None) -> None:
        """
        Unbans a server member/discord user

        IN:
            member - the member to unban
            reason - the ban reason
        """
        try:
            ban_entry = await ctx.guild.fetch_ban(member)

        except discord.NotFound:
            response_unbanned = RESPONSE_NOBAN.format(member=member.mention)

        else:
            if reason:
                msg_unbanned = MSG_UNBANNED_WITH_REASON.format(guild=ctx.guild.name, reason=reason)
                response_unbanned = RESPONSE_UNBANNED_WITH_REASON.format(member=member.mention, reason=reason)

            else:
                msg_unbanned = MSG_UNBANNED.format(guild=ctx.guild.name)
                response_unbanned = RESPONSE_UNBANNED.format(member=member.mention)

            await ctx.guild.unban(member, reason=reason)

            if not member.bot:
                try:
                    await member.send(msg_unbanned)

                except discord.Forbidden:
                    response_unbanned += ATTENTION_NO_DM

        finally:
            await ctx.send(response_unbanned, reference=ctx.message)

    @commands.command(name="purge")
    @commands.has_guild_permissions(manage_messages=True)
    @commands.bot_has_guild_permissions(manage_messages=True)
    @commands.guild_only()
    async def cmd_purge(self, ctx: commands.Context, limit: int, *, target: Optional[MemberOrUserConverter] = None) -> None:
        """
        Goes through the last messages and deletes them

        IN:
            limit - the number of messages to go through. Maximum 100, if you specify target, then maximum 200
            target - the messages' author, if specified, deletes messages only from that person
        """
        max_limit = 100 if target is None else 200
        limit = max(min(limit, max_limit), 0)
        check = lambda message: target is None or message.author == target

        deleted_msgs = await ctx.channel.purge(limit=limit, check=check)
        total_deleted = len(deleted_msgs)
        ending = "" if total_deleted == 1 else "s"

        try:
            og_message = await ctx.channel.fetch_message(ctx.message.id)

        except discord.NotFound:
            og_message = None

        await ctx.send(f"Deleted {total_deleted} message{ending}.", reference=og_message)


def setup(bot: Bot):
    for cog in _cogs:
        bot.add_cog(cog(bot))

def teardown(bot: Bot):
    for cog in _cogs:
        bot.remove_cog(cog(bot))
