"""
This modules contains constants for BoopliBot
"""

import discord


FOLDER_MODULES = "modules"
FOLDER_BOOPLIBOT = "BoopliBot"

EMB_COLOR_GREEN = discord.Color.green()
EMB_COLOR_ORANGE = discord.Color.orange()
EMB_COLOR_RED = discord.Color.red()

EMB_NAME_LIMIT = 256
EMB_VALUE_LIMIT = 1024
EMB_TITLE_LIMIT = 256
EMB_DESC_LIMIT = 2048
EMB_FOOTER_LIMIT = 2048
EMB_TOTAL_LIMIT = 6000
EMB_FIELDS_LIMIT = 25

EMPTY_EMBED_VALUE = "_ _"
ZERO_WIDTH_CHAR = "\u200b"

TIME_FMT = "%A, %d %B %Y %H:%M:%S:%f"

BOOPLIBOT_GITHUB = "https://github.com/Booplicate/BoopliBot"
BOOPLIBOT_DEF_PREMISSIONS = discord.Permissions(
    kick_members=True,
    ban_members=True,
    add_reactions=True,
    view_audit_log=True,
    read_messages=True,
    send_messages=True,
    manage_messages=True,
    read_message_history=True,
    embed_links=True,
    attach_files=True,
    mention_everyone=True,
    external_emojis=True,
    change_nickname=True,
    manage_nicknames=True,
    manage_roles=True,
    manage_emojis=True
)
