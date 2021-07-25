"""
Module contains the main classes for BoopliBot
"""

import sys
import asyncio
import logging
# import datetime
from typing import (
    Optional,
    Set
)


import discord
from discord.ext import commands


import BoopliBot
# from .helpcommand import HelpCommand
from .converters import MemberOrUserConverter
from .consts import FOLDER_MODULES, FOLDER_BOOPLIBOT
from . import errors
from .extra_classes import PartialAuditLogEntry, NestedDictWrapper
from .utils import (
    config_utils,
    sql_utils,
    retrieve_modules,
    get_audit_log_for_action
)


# logger = logging.getLogger(__name__)


class Bot(commands.AutoShardedBot):
    """
    Main class representing our discord bot
    """
    DEF_ACTIVITY = discord.Game(name=BoopliBot.__version__)
    DEF_INTENTS = discord.Intents.all()

    # We can use 64-113 and 0
    EXIT_CODE_QUIT = 0
    EXIT_CODE_CRASH = 1
    EXIT_CODE_RESTART = 65

    _instance = None

    def __new__(cls, *args, **kwargs):
        """
        Instance creation method override for singleton support
        """
        if cls._instance is not None:
            raise errors.BotAlreadyExists()

        self = super().__new__(cls)
        cls._instance = self

        return self

    def __init__(self, config: config_utils.Config) -> None:
        """
        Constructor
        """
        # if "help_command" not in kwargs:
        #     kwargs["help_command"] = HelpCommand()

        self.config = config

        kwargs = config.to_dict()
        kwargs.pop("token")
        self.def_prefix = kwargs.pop("def_prefix")
        activity_text = kwargs.pop("activity_text", None)
        if activity_text:
            activity = discord.Game(name=activity_text)
        else:
            activity = Bot.DEF_ACTIVITY

        super().__init__(
            command_prefix=Bot.__get_prefixes,
            activity=activity,
            intents=Bot.DEF_INTENTS,
            **kwargs
        )

        self.guilds_configs = NestedDictWrapper(nesting_depth=1)
        self.custom_commands = NestedDictWrapper(nesting_depth=1)

        self.exit_code = Bot.EXIT_CODE_CRASH
        self.cache_ready_lock = asyncio.Event()

        self.load_modules()

        self.logger = logging.getLogger(f"{__name__}.{type(self).__name__}")
        self.logger.info("Inited BoopliBot.")

    def __repr__(self) -> str:
        """
        Repr override
        """
        return f"{type(self).__name__}({self.config})"

    def __del__(self):
        """
        Destructor (don't really need it, but why not right)
        """
        Bot._instance = None

    def load_modules(self) -> None:
        """
        Loads modules from disk. This happens during init,
            for delayed module loading consider using the on_ready callback
        """
        for m in retrieve_modules():
            # Skip private modules
            if not m.startswith("_"):
                self.load_extension(f".{FOLDER_MODULES}.{m}", package=f"{FOLDER_BOOPLIBOT}")

    @staticmethod
    def __get_prefixes(bot, msg: discord.Message) -> Set[str]:
        """
        """
        prefixes = {bot.user.mention, f"<@!{bot.user.id}>"}

        guild = msg.guild
        if guild is not None:
            # NOTE: This may be None in the moment we join the guild
            guild_prefix = bot.guilds_configs[guild.id].prefix or bot.def_prefix
            prefixes.add(guild_prefix)

        return prefixes

    async def validate_db(self) -> None:
        """
        Validates tables in our datebase (e.g. for missing guild rows)
        NOTE: should be ran before loading cache
        """
        all_guilds_ids = [g.id for g in self.guilds]
        missing_guilds_id = set(all_guilds_ids)

        # First, check guilds configs
        async with sql_utils.NewAsyncSession() as sesh:
            sesh: sql_utils.AsyncSession
            STEP = 5000
            offset = 0
            while True:
                # rows = sesh.query(sql_utils.GuildConfig)[bottom_bracket:top_bracket]
                stmt = (
                    sql_utils.select(sql_utils.GuildConfig.guild_id)
                    .where(sql_utils.GuildConfig.guild_id.in_(all_guilds_ids))
                    .offset(offset)
                    .limit(STEP)
                )
                result = await sesh.execute(stmt)
                db_guilds_ids = set(result.scalars().all())
                if not db_guilds_ids:
                    break

                missing_guilds_id -= db_guilds_ids
                offset += STEP

            # Still have ids? Means we're missing some rows in our db
            if missing_guilds_id:
                # First, we log it
                missing_guilds_fmt = ", ".join(map(str, missing_guilds_id))
                self.logger.warning(f"Some guilds are missing from the datebase, adding them:\n    {missing_guilds_fmt}.")
                # Now fix it
                prefix = self.def_prefix
                # sesh.bulk_insert_mappings(
                #     sql_utils.GuildConfig,
                #     (dict(guild_id=guild_id, prefix=prefix) for guild_id in missing_guilds_id),
                #     return_defaults=False
                # )
                # TODO: This is kinda slow for an async function,
                # Consider using threading if it's too bad
                sesh.add_all(
                    (
                        sql_utils.GuildConfig(guild_id=guild_id, prefix=prefix)
                        for guild_id in missing_guilds_id
                    )
                )
                await sesh.commit()

        # TODO: Add more as needed here
        return

    async def load_cache(self) -> None:
        """
        Loads various guilds settings from the db in cache
        """
        all_guilds_ids = [g.id for g in self.guilds]
        async with sql_utils.NewAsyncSession() as sesh:
            # First load guilds configs
            # results = (
            #     sesh.query(sql_utils.GuildConfig)
            #     .filter(sql_utils.GuildConfig.guild_id.in_(all_guilds_ids))
            # )
            sesh: sql_utils.AsyncSession
            stmt = (
                sql_utils.select(sql_utils.GuildConfig)
                .where(sql_utils.GuildConfig.guild_id.in_(all_guilds_ids))
            )
            results = await sesh.execute(stmt)
            for guild_config in results.scalars().all():
                guild_config: sql_utils.GuildConfig

                self.guilds_configs[guild_config.guild_id] = NestedDictWrapper(
                    sql_utils.to_dict(guild_config),
                    nesting_depth=0
                )
            del stmt, results

            # Now load custom commands
            # results = (
            #     sesh.query(sql_utils.CustomCommand)
            #     .filter(sql_utils.CustomCommand.guild_id.in_(all_guilds_ids))
            # )
            stmt = (
                sql_utils.select(sql_utils.CustomCommand)
                .where(sql_utils.CustomCommand.guild_id.in_(all_guilds_ids))
            )
            results = await sesh.execute(stmt)
            for cmd in results.scalars().all():
                cmd: sql_utils.CustomCommand
                self.custom_commands[cmd.guild_id] = NestedDictWrapper(
                    sql_utils.to_dict(cmd),
                    nesting_depth=0
                )
            del stmt, results

    async def on_ready(self) -> None:
        """
        Callback when we loaded data from Discord and are ready to go
        """
        # Reset this flag in case of reconnect
        self.cache_ready_lock.clear()

        # We always want to have owner id
        if not self.owner_id and not self.owner_ids:
            app = await self.application_info()
            team = app.team
            if team is not None:
                self.owner_ids = {m.id for m in team.members}

            else:
                self.owner_id = app.owner.id

        # First, let's verify we have an entry in our db for every guild we're in
        await self.validate_db()
        # Now load db cache
        await self.load_cache()

        # Now we're listening to commands
        self.cache_ready_lock.set()

    async def process_commands(self, message: discord.Message):
        """
        Processes commands only after our cache is ready

        IN:
            message - message object
        """
        await self.cache_ready_lock.wait()
        await super().process_commands(message)

    async def on_message(self, message: discord.Message) -> None:
        """
        New message callback

        IN:
            message - message object
        """
        await super().on_message(message)

    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        """
        Message edit callback

        IN:
            before - message object before edit
            after - message object after edit
        """
        # We ignore msgs pins and attachments changes
        # I did it this way, so even if actual content wasn't changed,
        # we still reinvoke the command
        if (
            before.pinned != after.pinned
            or before.attachments != after.attachments
            or before.embeds != after.embeds
        ):
            return

        await self.process_commands(after)

    async def on_guild_join(self, guild: discord.Guild) -> None:
        """
        Callback when the bot joins/creates a guild

        IN:
            guild - the guild
        """
        guild_id = guild.id
        prefix = self.def_prefix

        async with sql_utils.NewAsyncSession() as sesh:
            sesh: sql_utils.AsyncSession
            # Try to get a config for this guild
            guild_config = await sesh.get(sql_utils.GuildConfig, guild_id)
            # If doesn't exist, create a new one
            if guild_config is None:
                guild_config = sql_utils.GuildConfig(guild_id=guild_id, prefix=prefix)
                sesh.add(guild_config)
                await sesh.commit()
                # guild_config = await sesh.get(sql_utils.GuildConfig, guild_id)

            # Add to cache
            self.guilds_configs[guild_config.guild_id] = NestedDictWrapper(
                sql_utils.to_dict(guild_config),
                nesting_depth=0
            )

    async def on_member_remove(self, member: discord.Member) -> None:
        """
        Callback on user leaving
        NOTE: ban/kick/leaving - all falls under this
        NOTE: discord doesn't provide a kick event, we have to
            workaround here with auditlogs...

        IN:
            member - the member who left the guild
        """
        guild: discord.Guild = member.guild

        # Check for custom kick event
        entry = await get_audit_log_for_action(guild, discord.AuditLogAction.kick, member)
        if entry is not None:
            self.dispatch("member_kick", guild, member, entry)
            return

        # Check for custom member left event
        try:
            await guild.fetch_ban(member)

        except discord.NotFound:
            self.dispatch("member_left", member)
            return

    ### HANDLERS FOR DB UPDATES

    async def on_member_warn(self, guild: discord.Guild, member: MemberOrUserConverter, log_entry: PartialAuditLogEntry) -> None:
        """
        Callback on user warn
        NOTE: custom event

        IN:
            guild - Guild object
            member - either User or Member object
        """
        # Update db
        guild_id = guild.id
        user_id = member.id
        async with sql_utils.NewAsyncSession() as sesh:
            sesh: sql_utils.AsyncSession

            user_data = await sesh.get(sql_utils.User, (guild_id, user_id))

            if user_data is not None:
                user_data.current_warns += 1
                user_data.total_warns += 1

            else:
                user_data = sql_utils.User(guild_id=guild_id, user_id=user_id, current_warns=1, total_warns=1)
                sesh.add(user_data)

            await sesh.commit()

    async def on_member_unwarn(self, guild: discord.Guild, member: MemberOrUserConverter, log_entry: PartialAuditLogEntry) -> None:
        """
        Callback on user unwarn
        NOTE: custom event

        IN:
            guild - Guild object
            member - either User or Member object
        """
        guild_id = guild.id
        user_id = member.id
        async with sql_utils.NewAsyncSession() as sesh:
            sesh: sql_utils.AsyncSession

            user_data = await sesh.get(sql_utils.User, (guild_id, user_id))

            if user_data is not None and user_data.current_warns > 0:
                user_data.current_warns -= 1
                await sesh.commit()

    async def on_member_kick(self, guild: discord.Guild, member: MemberOrUserConverter, log_entry: Optional[discord.AuditLogEntry] = None) -> None:
        """
        Callback on user kick
        NOTE: custom event

        IN:
            guild - Guild object
            member - Member object
        """
        # Update db
        guild_id = guild.id
        user_id = member.id
        async with sql_utils.NewAsyncSession() as sesh:
            sesh: sql_utils.AsyncSession

            user_data = await sesh.get(sql_utils.User, (guild_id, user_id))

            if user_data is not None:
                user_data.total_kicks += 1

            else:
                user_data = sql_utils.User(guild_id=guild_id, user_id=user_id, total_kicks=1)
                sesh.add(user_data)

            await sesh.commit()

    async def on_member_ban(self, guild: discord.Guild, member: MemberOrUserConverter) -> None:
        """
        Callback on user ban

        IN:
            guild - Guild object
            member - either User or Member object
        """
        log_entry = await get_audit_log_for_action(guild, discord.AuditLogAction.ban, member)

        # Update db
        guild_id = guild.id
        user_id = member.id
        async with sql_utils.NewAsyncSession() as sesh:
            sesh: sql_utils.AsyncSession

            user_data = await sesh.get(sql_utils.User, (guild_id, user_id))

            if user_data is not None:
                user_data.total_bans += 1

            else:
                user_data = sql_utils.User(guild_id=guild_id, user_id=user_id, total_bans=1)
                sesh.add(user_data)

            await sesh.commit()

        self.dispatch(
            "member_ban_custom",
            guild,
            member,
            log_entry
        )

    async def on_member_unban(self, guild: discord.Guild, user: discord.User) -> None:
        """
        Callback on user unban

        IN:
            guild - Guild object
            user - User object
        """
        log_entry = await get_audit_log_for_action(guild, discord.AuditLogAction.unban, user)
        self.dispatch(
            "member_unban_custom",
            guild,
            user,
            log_entry
        )

    ### ERROR HANDLERS

    async def on_error(self, event, *args, **kwargs) -> None:
        """
        Default error error handler for events errors
        """
        exc_type, exc, tb = sys.exc_info()
        self.logger.error(f"Got unexpected exception in the '{event}' event: {repr(exc)}", exc_info=exc)

    async def on_command_error(self, context: commands.Context, exc: Exception) -> None:
        """
        Default error handler for command errors

        IN:
            context - the command context object
            exc - the exception
        """
        if self.extra_events.get("on_command_error", None):
            return

        if hasattr(context.command, "on_error"):
            return

        cog = context.cog
        if cog and commands.Cog._get_overridden_method(cog.cog_command_error) is not None:
            return

        command = context.command

        if isinstance(exc, commands.CommandNotFound):
            pass

        elif isinstance(exc, errors.MissingRequiredSubCommand):
            sub_cmds = "/".join((sub_cmd.name for sub_cmd in command.commands))
            await context.send(
                f"Missing required subcommand. Correct syntax: `{context.prefix}{command.qualified_name} <{sub_cmds}>`."
            )

        elif isinstance(exc, commands.MissingRequiredArgument):
            await context.send(
                f"Missing required argument: `{exc.param.name}`. Correct syntax: `{context.prefix}{command.qualified_name} {command.signature}`."
            )

        elif isinstance(exc, commands.RoleNotFound):
            role = discord.utils.escape_mentions(exc.argument)
            await context.send(f"A role **{role}** was not found.")

        elif isinstance(exc, errors.BadRole):
            role = discord.utils.escape_mentions(exc.argument.name)
            await context.send(f"The role **{role}** cannot be used in this command.")

        elif isinstance(exc, commands.MemberNotFound):
            member = discord.utils.escape_mentions(exc.argument)
            await context.send(f"A member **{member}** was not found.")

        elif isinstance(exc, commands.UserNotFound):
            user = discord.utils.escape_mentions(exc.argument)
            await context.send(f"A user **{user}** was not found.")

        elif isinstance(exc, errors.MemberOrUserNotFound):
            memberuser = discord.utils.escape_mentions(exc.argument)
            await context.send(f"A member or user **{memberuser}** was not found.")

        elif isinstance(exc, commands.EmojiNotFound):
            emoji = discord.utils.escape_mentions(exc.argument)
            await context.send(f"An emote **{emoji}** was not found.")

        elif isinstance(exc, discord.Forbidden):
            await context.send("Forbidden. I may need more permissions for this action.")

        elif isinstance(exc, commands.BotMissingPermissions):
            perms = [
                f"**{perm.replace('_', ' ').replace('guild', 'server').title()}**"
                for perm in exc.missing_perms
            ]
            if len(perms) > 2:
                fmt = "{}, and {}".format(", ".join(perms[:-1]), perms[-1])
            else:
                fmt = " and ".join(perms)

            await context.send(f"I am missing permission(s) for this command: {fmt}.")

        elif isinstance(exc, errors.BotTooLowInHierarchy):
            await context.send("I cannot use this command on members with the same or a higher top role than I have.")

        elif isinstance(exc, commands.NoPrivateMessage):
            await context.send(f"Command `{command.qualified_name}` cannot be used in private messages.")

        elif isinstance(exc, commands.NotOwner):
            await context.send("You don't have permissions for this command.")

        elif isinstance(exc, errors.MissingPermissionsAndNotOnSelf):
            await context.send("You don't have permissions to use this command on other people.")

        elif isinstance(exc, errors.TooLowInHierarchy):
            await context.send("You cannot use this commands on members with the same or a higher top role than you have.")

        elif isinstance(exc, commands.CommandOnCooldown):
            await context.send(f"This command is on cooldown. Try again in **{exc.retry_after:0.2f}** second(s).")

        else:
            exc_repr = repr(exc)
            self.logger.error(f"Got unexpected exception in the '{context.command}' command: {exc_repr}", exc_info=exc)
            await context.send(f"Got unexpected exception: **{exc_repr}**")

        return
