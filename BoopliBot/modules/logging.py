"""
Module contains cog for chat logs.
"""

# import datetime
from textwrap import shorten as shorten_text
from typing import (
    Tuple,
    Optional,
    Union
)

import discord
from discord.ext import commands
from discord.utils import utcnow


import BoopliBot
from ..bot import Bot
from .. import consts
from ..utils import (
    register_cog,
    fmt_datetime
)
from ..converters import MemberOrUserConverter
from ..extra_classes import PartialAuditLogEntry


_cogs = set()


class _LogEmbedBuilder():
    """
    A namespace for embed building methods
    """
    @staticmethod
    def _validate_field(embed_len: int, field_name: str, field_value: str, placeholder: str = "[...]") -> Tuple[str]:
        """
        Validates that the given name and value are within discord embed limits
        Shorten them if needed
        NOTE: raises ValueError if there's no place for this field

        IN:
            embed_len - total len of all embed fields, titles, description, etc
            field_value - the field value to check
            placeholder - the placeholder for the cut part of the string

        OUT:
            tuple of str, the adjusted name and value
        """
        name_len = len(field_name)
        if name_len > consts.EMB_NAME_LIMIT:
            field_name = shorten_text(field_name, width=consts.EMB_NAME_LIMIT, placeholder=placeholder)
            name_len = len(field_name)

        value_len = len(field_value)
        if value_len > consts.EMB_VALUE_LIMIT:
            field_value = shorten_text(field_value, width=consts.EMB_VALUE_LIMIT, placeholder=placeholder)
            value_len = len(field_value)

        limit = consts.EMB_TOTAL_LIMIT - (embed_len + name_len)
        if value_len > limit:
            if limit < 0 or limit < len(placeholder):
                raise ValueError("Can't fit another field in the embed.")
            field_value = shorten_text(field_value, width=limit, placeholder=placeholder)

        return field_name, field_value

    @staticmethod
    def _get_base_embed(title: str) -> discord.Embed:
        """
        Builds a base embed for all logs
        """
        return (
            discord.Embed(title=f"Log: {title}")
            .set_footer(text=fmt_datetime(utcnow()))
        )

    @classmethod
    def _get_base_msg_embed(
        cls,
        title: str,
        message: discord.Message
    ) -> discord.Embed:
        """
        Builds a base embed for msg logs
        """
        member = message.author
        channel = message.channel
        return (
            cls._get_base_embed(title)
            .set_thumbnail(url=member.avatar_url)
            .add_field(name="User:", value=member.mention, inline=False)
            .add_field(name="User ID:", value=f"{member.id}", inline=False)
            # .add_field(name=consts.EMPTY_EMBED_VALUE, value=consts.EMPTY_EMBED_VALUE, inline=False)
            .add_field(name="Channel:", value=channel.mention, inline=False)
            .add_field(name="Message ID:", value=f"[{message.id}]({message.jump_url} 'Click to jump to the message')", inline=False)
        )

    @classmethod
    def get_msg_edit_embed(
        cls,
        old_message: discord.Message,
        new_message: discord.Message
    ) -> Optional[discord.Embed]:
        """
        Builds an embed for msg edit logs

        IN:
            old_message - the original msg
            new_message - the new msg

        OUT:
            Embed or None
        """
        embed = cls._get_base_msg_embed("Message Edited", old_message)
        old_content = old_message.content
        new_content = new_message.content
        old_attachments = set(old_message.attachments)
        new_attachments = set(new_message.attachments)
        is_valid_embed = False

        if old_content != new_content:
            is_valid_embed = True
            old_content_field = "Old content:"
            new_content_field = "New content:"
            embed_len = len(embed)
            old_content_field, old_content = cls._validate_field(embed_len, old_content_field, old_content)
            # This may happen if someone added a text to a message with just an attachment
            if old_content:
                embed.add_field(name=old_content_field, value=old_content, inline=False)

            embed_len = len(embed)
            new_content_field, new_content = cls._validate_field(embed_len, new_content_field, new_content)
            # Or removed text, I guess?
            if not new_content:
                new_content = consts.ZERO_WIDTH_CHAR

            embed.add_field(name=new_content_field, value=new_content, inline=False)

        if old_attachments != new_attachments:
            is_valid_embed = True
            fields_data = (
                # For removed attachments
                {
                    "files": tuple(old_attachments - new_attachments),
                    "field_names": ("Removed image:", "Removed multiple images:")
                },
                # For added attachments
                {
                    "files": tuple(new_attachments - old_attachments),
                    "field_names": ("Added image:", "Added multiple images:")
                }
            )
            for data in fields_data:
                files = data["files"]
                if len(files) > 0:
                    if len(files) == 1:
                        # If there's a single img, we attach it
                        field_name = data["field_names"][0]
                        img_url = files[0].proxy_url
                        embed.add_field(name=field_name, value=consts.ZERO_WIDTH_CHAR, inline=False)
                        embed.set_image(url=img_url)

                    else:
                        # If there's multiple imgs, we just send their urls
                        field_name = data["field_names"][1]
                        imgs_links = "\n".join((f.proxy_url for f in files))
                        embed_len = len(embed)
                        field_name, imgs_links = cls._validate_field(embed_len, field_name, imgs_links)
                        embed.add_field(name=field_name, value=imgs_links, inline=False)

        return embed if is_valid_embed else None

    @classmethod
    def get_msg_del_embed(cls, message: discord.Message) -> Optional[discord.Embed]:
        """
        Builds an embed for msg deletion logs

        IN:
            message - the deleted msg

        OUT:
            Embed or None
        """
        embed = cls._get_base_msg_embed("Message Deleted", message)
        embed_len = len(embed)
        content = message.content
        attachments = message.attachments
        is_valid_embed = False

        if content:
            is_valid_embed = True
            field_name = "Content:"
            field_name, content = cls._validate_field(embed_len, field_name, content)
            embed.add_field(name=field_name, value=content, inline=False)

        if len(attachments) > 0:
            is_valid_embed = True
            if len(attachments) == 1:
                field_name = "Attachment:"
                embed.add_field(name=field_name, value=consts.ZERO_WIDTH_CHAR, inline=False)
                embed.set_image(url=attachments[0].proxy_url)

            else:
                embed_len = len(embed)
                field_name = "Attachments:"
                imgs_links = "\n".join((f.proxy_url for f in attachments))
                field_name, imgs_links = cls._validate_field(embed_len, field_name, imgs_links)
                embed.add_field(name=field_name, value=imgs_links, inline=False)

        return embed if is_valid_embed else None

    @classmethod
    def _get_user_join_left_embed(cls, title: str, member: discord.Member) -> discord.Embed:
        """
        Builds an embed for user join/leaving logs
        """
        return (
            cls._get_base_embed(title)
            .set_thumbnail(url=member.avatar_url)
            .add_field(name="User:", value=member.mention, inline=False)
            .add_field(name="User ID:", value=f"{member.id}", inline=False)
        )

    @classmethod
    def get_user_join_embed(cls, member: discord.Member) -> discord.Embed:
        """
        Builds an embed for user join logs
        """
        return cls._get_user_join_left_embed("User Has Joined", member)

    @classmethod
    def get_user_left_embed(cls, member: discord.Member) -> discord.Embed:
        """
        Builds an embed for user leaving logs
        """
        return cls._get_user_join_left_embed("User Has Left", member)

    @classmethod
    def _get_mod_action_embed(
        cls,
        title: str,
        member: discord.Member,
        log_entry: Union[PartialAuditLogEntry, discord.AuditLogEntry, None]
    ) -> discord.Embed:
        """
        Builds a base embed for warns/kicks/bans
        """
        moderator = "Unknown"
        reason = "Unknown"

        if log_entry is not None:
            user = log_entry.user
            if isinstance(user, (discord.Member, discord.User)):
                moderator = user.mention

            elif user:
                moderator = user

            if log_entry.reason:
                reason = log_entry.reason

        reason = shorten_text(reason, width=consts.EMB_VALUE_LIMIT, placeholder="[...]")

        return (
            cls._get_base_embed(title)
            .set_thumbnail(url=member.avatar_url)
            .add_field(name="User:", value=member.mention, inline=False)
            .add_field(name="By:", value=moderator, inline=False)
            .add_field(name="With Reason:", value=reason, inline=False)
        )

    @classmethod
    def get_warn_embed(cls, member: discord.Member, log_entry: PartialAuditLogEntry) -> discord.Embed:
        """
        Builds an embed for warn event
        """
        return cls._get_mod_action_embed("User Has Been Warned", member, log_entry)

    @classmethod
    def get_unwarn_embed(cls, member: discord.Member, log_entry: PartialAuditLogEntry) -> discord.Embed:
        """
        Builds an embed for unwarn event
        """
        return cls._get_mod_action_embed("User Has Been Unwarned", member, log_entry)

    @classmethod
    def get_kick_embed(cls, member: discord.Member, log_entry: discord.AuditLogEntry) -> discord.Embed:
        """
        Builds an embed for kick event
        """
        return cls._get_mod_action_embed("User Has Been Kicked", member, log_entry)

    @classmethod
    def get_ban_embed(cls, member: discord.Member, log_entry: Optional[discord.AuditLogEntry]) -> discord.Embed:
        """
        Builds an embed for ban event
        """
        return cls._get_mod_action_embed("User Has Been Banned", member, log_entry)

    @classmethod
    def get_unban_embed(cls, member: discord.Member, log_entry: Optional[discord.AuditLogEntry]) -> discord.Embed:
        """
        Builds an embed for unban event
        """
        return cls._get_mod_action_embed("User Has Been Unbanned", member, log_entry)


@register_cog(_cogs)
class Logger(commands.Cog, command_attrs=dict(hidden=True)):
    """
    Logger contains methods for chat logs handling
    """
    def __init__(self, bot: Bot):
        """
        Constructor

        IN:
            bot - the bot object
        """
        self.bot = bot

    # @commands.Cog.listener(name="on_raw_message_edit")
    # async def on_raw_message_edit(self, payload):
    #     from pprint import pprint
    #     pprint(payload.data)

    @commands.Cog.listener(name="on_message_edit")
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        """
        Callback on message editing

        IN:
            before - the message before edit
            after - the message after edit
        """
        # Don't log bots messages
        if before.author.bot:
            return

        guild: discord.Guild = before.guild
        # Only log guild msgs
        if guild is None:
            return

        log_channel = self.bot.guilds_configs[guild.id].log_channel
        # No log channel means logging is disabled
        log_channel: Optional[discord.TextChannel] = guild.get_channel(log_channel)
        if log_channel is None:
            return

        embed = _LogEmbedBuilder.get_msg_edit_embed(before, after)
        if embed is not None:
            await log_channel.send(embed=embed)

    @commands.Cog.listener(name="on_message_delete")
    async def on_message_delete(self, message: discord.Message) -> None:
        """
        Calblack on message deleting

        IN:
            message - the deleted message
        """
        if message.author.bot:
            return

        guild: discord.Guild = message.guild
        if guild is None:
            return

        log_channel = self.bot.guilds_configs[guild.id].log_channel
        log_channel: Optional[discord.TextChannel] = guild.get_channel(log_channel)
        if log_channel is None:
            return

        embed = _LogEmbedBuilder.get_msg_del_embed(message)
        if embed is not None:
            await log_channel.send(embed=embed)

    @commands.Cog.listener(name="on_member_join")
    async def on_member_join(self, member: discord.Member) -> None:
        """
        Callback on user joining the guid

        IN:
            member - the member who joined
        """
        guild: discord.Guild = member.guild
        if guild is None:
            return

        log_channel: Optional[int] = self.bot.guilds_configs[guild.id].log_channel
        log_channel: Optional[discord.TextChannel] = guild.get_channel(log_channel)
        if log_channel is None:
            return

        embed = _LogEmbedBuilder.get_user_join_embed(member)
        await log_channel.send(embed=embed)

    @commands.Cog.listener(name="on_member_left")
    async def on_member_left(self, member: discord.Member) -> None:
        """
        Callback on user leaving the guild
        NOTE: custom event

        IN:
            member - the member
        """
        guild: discord.Guild = member.guild
        if guild is None:
            return

        log_channel: Optional[int] = self.bot.guilds_configs[guild.id].log_channel
        log_channel: Optional[discord.TextChannel] = guild.get_channel(log_channel)
        if log_channel is None:
            return

        embed = _LogEmbedBuilder.get_user_left_embed(member)
        await log_channel.send(embed=embed)

    @commands.Cog.listener(name="on_member_warn")
    async def on_member_warn(self, guild: discord.Guild, member: MemberOrUserConverter, log_entry: PartialAuditLogEntry) -> None:
        """
        Callback on user warn
        NOTE: custom event

        IN:
            guild - Guild object
            member - either User or Member object
            log_entry - the audit log entry
                (Default: None)
        """
        log_channel: Optional[int] = self.bot.guilds_configs[guild.id].log_channel
        log_channel: Optional[discord.TextChannel] = guild.get_channel(log_channel)
        if log_channel is None:
            return

        embed = _LogEmbedBuilder.get_warn_embed(member, log_entry)
        await log_channel.send(embed=embed)

    @commands.Cog.listener(name="on_member_unwarn")
    async def on_member_unwarn(self, guild: discord.Guild, member: MemberOrUserConverter, log_entry: PartialAuditLogEntry) -> None:
        """
        Callback on user unwarn
        NOTE: custom event

        IN:
            guild - Guild object
            member - either User or Member object
            log_entry - the audit log entry
                (Default: None)
        """
        log_channel: Optional[int] = self.bot.guilds_configs[guild.id].log_channel
        log_channel: Optional[discord.TextChannel] = guild.get_channel(log_channel)
        if log_channel is None:
            return

        embed = _LogEmbedBuilder.get_unwarn_embed(member, log_entry)
        await log_channel.send(embed=embed)

    @commands.Cog.listener(name="on_member_kick")
    async def on_member_kick(self, guild: discord.Guild, member: discord.Member, log_entry: discord.AuditLogEntry) -> None:
        """
        Callback on user kick
        NOTE: custom event

        IN:
            guild - Guild object
            member - Member object
            log_entry - the audit log entry
        """
        log_channel: Optional[int] = self.bot.guilds_configs[guild.id].log_channel
        log_channel: Optional[discord.TextChannel] = guild.get_channel(log_channel)
        if log_channel is None:
            return

        embed = _LogEmbedBuilder.get_kick_embed(member, log_entry)
        await log_channel.send(embed=embed)

    @commands.Cog.listener(name="on_member_ban_custom")
    async def on_member_ban(self, guild: discord.Guild, member: discord.Member, log_entry: Optional[discord.AuditLogEntry] = None) -> None:
        """
        Callback on user ban
        NOTE: custom event

        IN:
            guild - Guild object
            member - either User or Member object
            log_entry - the audit log entry (not passed in officially, only via our custom callback)
                (Default: None)
        """
        log_channel: Optional[int] = self.bot.guilds_configs[guild.id].log_channel
        log_channel: Optional[discord.TextChannel] = guild.get_channel(log_channel)
        if log_channel is None:
            return

        embed = _LogEmbedBuilder.get_ban_embed(member, log_entry)
        await log_channel.send(embed=embed)

    @commands.Cog.listener(name="on_member_unban_custom")
    async def on_member_unban(self, guild: discord.Guild, user: discord.User, log_entry: Optional[discord.AuditLogEntry] = None) -> None:
        """
        Callback on user unban
        NOTE: custom event

        IN:
            guild - Guild object
            user - User object
            log_entry - the audit log entry (not passed in officially, only via our custom callback)
                (Default: None)
        """
        log_channel: Optional[int] = self.bot.guilds_configs[guild.id].log_channel
        log_channel: Optional[discord.TextChannel] = guild.get_channel(log_channel)
        if log_channel is None:
            return

        embed = _LogEmbedBuilder.get_unban_embed(user, log_entry)
        await log_channel.send(embed=embed)


def setup(bot: Bot):
    for cog in _cogs:
        bot.add_cog(cog(bot))

def teardown(bot: Bot):
    for cog in _cogs:
        bot.remove_cog(cog(bot))
