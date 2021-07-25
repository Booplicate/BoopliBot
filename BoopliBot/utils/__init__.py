"""
Module where we keep utils methods (e.g. logging)
"""

import os
import sys
import json
import logging
import datetime
from typing import (
    Dict,
    List,
    Union,
    Any
)


import discord
from discord.ext import commands


import BoopliBot
from ..consts import (
    TIME_FMT,
    FOLDER_MODULES,
    FOLDER_BOOPLIBOT
)
from ..errors import BadBotPrefix, MissingPermissionsAndNotOnSelf


def str_add_dash_space(string: str) -> str:
    """
    Formats a string by adding a dash and a space
    """
    return f"- {string}"

def fmt_datetime(dt: datetime.datetime) -> str:
    """
    Formats datetime to a pretty string

    IN:
        dt - datetime object

    OUT:
        str
    """
    return dt.strftime(TIME_FMT)[:-3]

def validate_prefix(prefix: str) -> None:
    """
    """
    prefix = prefix.strip()

    if not prefix:
        raise BadBotPrefix("Prefix should consist of a minimum of 1 character.")

    if len(prefix) > 3:
        raise BadBotPrefix("Prefix should consist of a maximum of 3 characters.")

    if not prefix.isascii():
        raise BadBotPrefix("Prefix should consist of ascii characters, for example: `$`.")


def retrieve_modules() -> List[str]:
    """
    Retrieves modules from disk
    """
    modules = list()
    EXT = ".py"
    for file_ in os.listdir(f"{FOLDER_BOOPLIBOT}/{FOLDER_MODULES}"):
        if file_.endswith(EXT) and not file_.startswith("__"):
            modules.append(file_[:-len(EXT)])

    return modules

def register_cog(cog_set):
    """
    Decorator to register new cogs

    IN:
        cog_set - the set of cogs to add this cog to
    """
    def decorator(cog):
        cog_set.add(cog)
        return cog

    return decorator


async def get_audit_log_for_action(guild: discord.Guild, action: discord.AuditLogAction, target: discord.Member) -> Union[discord.AuditLogEntry, None]:
    """
    Returns the last audit log for the given action and target
    NOTE: coro

    IN:
        guild - the guid to fetch the log from
        action - the action
        target - the target member

    OUT:
        AuditLogEntry or None
    """
    now = datetime.datetime.utcnow()
    after = now - datetime.timedelta(minutes=15)

    log_iter = guild.audit_logs(
        limit=25,
        after=after,
        oldest_first=False,
        action=action
    )

    def predicate(entry: discord.AuditLogEntry) -> bool:
        return entry.target == target

    return await log_iter.find(predicate)


def is_owner_or_admin():
    """
    Check for high-level commands (for owners and admins)
    """
    async def predicate(ctx: commands.Context):
        bot = ctx.bot
        author = ctx.author
        return (
            (bot.owner_id and author.id == bot.owner_id)
            or (bot.owner_ids and author.id in bot.owner_ids)
            or author.guild_permissions.administrator
        )

    return commands.check(predicate)

def is_mod_or_used_on_self(invoked_by: discord.Member, used_on: Union[discord.Member, discord.User]) -> None:
    """
    This is a non-standad check. It has to be used inside commands instead of being
        used as a decorator. This is because Context doesn't have args and kwargs of the command
        when command checks are being invoked. Consider this a workaround, I guess.

    A user considered a mod if they have the kick member permission
    If this check fails, it raises MissingPermissionsAndNotOnSelf

    IN:
        invoked_by - the user who invokes this command
        used_on - the target used
    """
    if invoked_by != used_on and not invoked_by.guild_permissions.kick_members:
        raise MissingPermissionsAndNotOnSelf()
