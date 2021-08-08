"""
Module provides main set of commands. This module is required and must always be loaded.
"""

import asyncio
import traceback
import random
# from typing import (
#     List
#     # Union,
#     # Any,
#     # Optional
# )
import re


import discord
from discord.ext import commands


import BoopliBot
from .. import bot
from ..utils import (
    FOLDER_MODULES,
    str_add_dash_space,
    retrieve_modules,
    register_cog,
    is_owner_or_admin,
    validate_prefix,
    sql_utils
)
from ..consts import (
    EMB_COLOR_GREEN,
    EMB_COLOR_ORANGE,
    EMB_COLOR_RED,
    EMPTY_EMBED_VALUE,
    CODE_BLOCK_PATTERN
)
from ..errors import (
    MissingRequiredSubCommand,
    BadBotPrefix
)


_cogs = set()


@register_cog(_cogs)
class RootCommands(commands.Cog, name="Root"):
    """
    This collection provides root commands for BoopliBot
    """
    MODULES_UNLOAD_BLACKLIST = [
        __name__.rpartition(".")[-1]
    ]

    GOODBYE_MESSAGES = (
        "Shutting down...",
        "`Oh no`",
        "Not again!",
        "I don't want to die...",
        "Goodbye cruel world...",
        "It has been a privilege chatting with you tonight.",
        "You're next...",
        "`I'll be back`"
    )

    def __init__(self, bot: bot.Bot):
        """
        Constructor

        IN:
            bot - the bot object
        """
        self.bot = bot

    @commands.command(name="ping")
    @is_owner_or_admin()
    @commands.cooldown(rate=1, per=5, type=commands.cooldowns.BucketType.guild)
    async def cmd_ping(self, ctx: commands.Context) -> None:
        """
        Basic ping command
        """
        ping = round(self.bot.latency * 1000)

        embed = discord.Embed()
        embed.add_field(name=f"Pong! {ping} ms", value=EMPTY_EMBED_VALUE, inline=True)

        if ping < 150:
            color = EMB_COLOR_GREEN
        elif ping < 200:
            color = EMB_COLOR_ORANGE
        else:
            color = EMB_COLOR_RED
        embed.color = color

        await ctx.send(embed=embed, reference=ctx.message)

    @commands.command(name="prefix")
    @is_owner_or_admin()
    @commands.guild_only()
    async def cmd_prefix(self, ctx: commands.Context, new_prefix: str = None) -> None:
        """
        Sets a new prefix for commands on this server

        IN:
            new_prefix - string with the new prefix. If empty, sets the default prefix for BoopliBot
        """
        guild_id = ctx.guild.id

        if not new_prefix:
            new_prefix = self.bot.def_prefix
            response = "Reset command prefix back to"

        else:
            response = "Set command prefix to"

        new_prefix = new_prefix.strip()
        try:
            validate_prefix(new_prefix)
        except BadBotPrefix as e:
            await ctx.send(str(e), reference=ctx.message)
            return

        async with sql_utils.NewAsyncSession() as sesh:
            sesh: sql_utils.AsyncSession
            stmt = (
                sql_utils.update(sql_utils.GuildConfig)
                .values(prefix=new_prefix)
                .where(sql_utils.GuildConfig.guild_id == guild_id)
            )
            await sesh.execute(stmt)
            await sesh.commit()
            self.bot.guilds_configs[guild_id].prefix = new_prefix

        await ctx.send(f"{response} `{new_prefix}`.", reference=ctx.message)

    @commands.command(name="activity", aliases=("status", "game"))
    @commands.is_owner()
    async def cmd_activity(self, ctx: commands.Context, *, string: str = None) -> None:
        """
        Sets a new activity

        IN:
            string - string with the new activity. If empty, uses current bot version
        """
        if string:
            string = string.strip()
            activity = discord.Game(name=string)
            self.bot.config.activity_text = string

        else:
            activity = bot.Bot.DEF_ACTIVITY
            self.bot.config.activity_text = ""

        # TODO: replace run_in_executor with asyncio.to_thread
        ev_loop: asyncio.BaseEventLoop = asyncio.get_running_loop()
        await ev_loop.run_in_executor(None, self.bot.config.save_if_dirty)

        await self.bot.change_presence(activity=activity)

    @commands.command(name="shutdown", aliases=("die", "kill", "slep", "sleep"))
    @commands.is_owner()
    async def cmd_shutdown(self, ctx: commands.Context) -> None:
        """
        Shutdowns the bot
        """
        self.bot.exit_code = bot.Bot.EXIT_CODE_QUIT
        await ctx.channel.send(random.choice(RootCommands.GOODBYE_MESSAGES), reference=ctx.message)
        await self.bot.close()

    @commands.command(name="restart", aliases=("reload", "reboot"))
    @commands.is_owner()
    async def cmd_restart(self, ctx: commands.Context) -> None:
        """
        Restarts the bot
        """
        self.bot.exit_code = bot.Bot.EXIT_CODE_RESTART
        await ctx.channel.send("Restarting...", reference=ctx.message)
        await self.bot.close()

    @commands.group(name="module", aliases=("modules", "m"), invoke_without_command=True)
    @commands.is_owner()
    async def cmd_module(self, ctx: commands.Context) -> None:
        """
        Group of module operation commands

        TODO: I do not check for len of the message for the module group commands,
            but discord has a limit for embeds, should fix it at some point
        """
        if ctx.invoked_subcommand is None:
            raise MissingRequiredSubCommand()

    @cmd_module.command(name="stats", aliases=("s",))
    @commands.is_owner()
    async def cmd_module_stats(self, ctx: commands.Context) -> None:
        """
        Prints all the modules (both loaded and unloaded)
        """
        # Remove the 'modules.' prefix
        loaded_modules = [m_name.rpartition(".")[-1] for m_name in tuple(self.bot.extensions.keys())]
        unloaded_modules = retrieve_modules()
        # Remove already loaded modules
        unloaded_modules = set(unloaded_modules).difference(loaded_modules)

        embed = discord.Embed(title="Modules", color=EMB_COLOR_GREEN)

        if loaded_modules:
            embed.add_field(
                name=f"Loaded modules ({len(loaded_modules)}):",
                value="\n".join(map(str_add_dash_space, loaded_modules)),
                inline=False
            )

        else:
            embed.add_field(name="No loaded modules", value=EMPTY_EMBED_VALUE, inline=False)

        if unloaded_modules:
            embed.add_field(
                name=f"Unloaded modules ({len(unloaded_modules)}):",
                value="\n".join(map(str_add_dash_space, unloaded_modules)),
                inline=False
            )

        else:
            embed.add_field(name="No unloaded modules", value=EMPTY_EMBED_VALUE, inline=False)

        await ctx.send(embed=embed, reference=ctx.message)

    @cmd_module.command(name="load", aliases=("l",))
    @commands.is_owner()
    async def cmd_module_load(self, ctx: commands.Context, module: str, *modules: str) -> None:
        """
        Loads a module

        IN:
            module - the name of the module to load (* loads everything)
            modules - additional modules to load (optional)
        """
        succeed = list()
        failed = dict()
        folder_prefix = f".{FOLDER_MODULES}."

        if module == "*":
            modules = retrieve_modules()

        else:
            modules = (module,) + modules

        total_modules = len(modules)

        for m in modules:
            # For mass import we skip 'private' modules
            # as they are mostly for debugging
            if module == "*" and m.startswith("_"):
                failed[m] = "This module is private."
                continue

            # Handle prefix
            if not m.startswith(folder_prefix):
                full_m_name = folder_prefix + m

            else:
                full_m_name = m
                m = m[len(folder_prefix):]

            try:
                self.bot.load_extension(full_m_name, package="BoopliBot")

            except Exception as e:
                # Format the exp into a str and remove path prefix
                failed[m] = str(e).replace(f"BoopliBot.{FOLDER_MODULES}.", "")

            else:
                succeed.append(m)

        embed = discord.Embed(title="Loading modules")

        if succeed:
            embed.add_field(
                name=f"Successfully loaded the modules ({len(succeed)}/{total_modules}):",
                value="\n".join(map(str_add_dash_space, succeed)),
                inline=False
            )

        else:
            embed.add_field(name="No modules were loaded", value=EMPTY_EMBED_VALUE, inline=False)

        if failed:
            values = [
                f"{str_add_dash_space(m)} (reason: {failed[m]})"
                for m in failed
            ]
            embed.add_field(
                name=f"Failed to load the modules ({len(failed)}/{total_modules}):",
                value="\n".join(values),
                inline=False
            )

        if succeed and not failed:
            embed.color = EMB_COLOR_GREEN

        elif failed and not succeed:
            embed.color = EMB_COLOR_RED

        else:
            embed.color = EMB_COLOR_ORANGE

        await ctx.send(embed=embed, reference=ctx.message)

    @cmd_module.command(name="unload", aliases=("u",))
    @commands.is_owner()
    async def cmd_module_unload(self, ctx: commands.Context, module: str, *modules: str) -> None:
        """
        Unloads a module

        IN:
            module - the name of the module to unload (* unloads everything, but the main module)
            modules - additional modules to unload (optional)
        """
        succeed = list()
        failed = dict()
        folder_prefix = f".{FOLDER_MODULES}."

        if module == "*":
            modules = [m_name.rpartition(".")[-1] for m_name in tuple(self.bot.extensions.keys())]

        else:
            modules = (module,) + modules

        total_modules = len(modules)

        for m in modules:
            # Handle prefix
            if not m.startswith(folder_prefix):
                full_m_name = folder_prefix + m

            else:
                full_m_name = m
                m = m[len(folder_prefix):]

            if m in RootCommands.MODULES_UNLOAD_BLACKLIST:
                failed[m] = "This module cannot be unloaded."
                continue

            try:
                self.bot.unload_extension(full_m_name, package="BoopliBot")

            except Exception as e:
                # Format the exp into a str and remove path prefix
                failed[m] = str(e).replace(f"BoopliBot.{FOLDER_MODULES}.", "")

            else:
                succeed.append(m)

        embed = discord.Embed(title="Unloading modules")

        if succeed:
            embed.add_field(
                name=f"Successfully unloaded the modules ({len(succeed)}/{total_modules}):",
                value="\n".join(map(str_add_dash_space, succeed)),
                inline=False
            )

        else:
            embed.add_field(name="No modules were unloaded", value=EMPTY_EMBED_VALUE, inline=False)

        if failed:
            values = [
                f"{str_add_dash_space(m)} (reason: {failed[m]})"
                for m in failed
            ]
            embed.add_field(
                name=f"Failed to unload the modules ({len(failed)}/{total_modules}):",
                value="\n".join(values),
                inline=False
            )

        if succeed and not failed:
            embed.color = EMB_COLOR_GREEN

        elif failed and not succeed:
            embed.color = EMB_COLOR_RED

        else:
            embed.color = EMB_COLOR_ORANGE

        await ctx.send(embed=embed, reference=ctx.message)

    @cmd_module.command(name="reload", aliases=("r",))
    @commands.is_owner()
    async def cmd_module_reload(self, ctx: commands.Context, module: str, *modules: str) -> None:
        """
        Reloads a module

        IN:
            module - the name of the module to reload (* reloads everything)
            modules - additional modules to reload (optional)
        """
        succeed = list()
        failed = dict()
        folder_prefix = f".{FOLDER_MODULES}."

        if module == "*":
            modules = [m_name.rpartition(".")[-1] for m_name in tuple(self.bot.extensions.keys())]

        else:
            modules = (module,) + modules

        total_modules = len(modules)

        for m in modules:
            # Handle prefix
            if not m.startswith(folder_prefix):
                full_m_name = folder_prefix + m

            else:
                full_m_name = m
                m = m[len(folder_prefix):]

            try:
                self.bot.reload_extension(full_m_name, package="BoopliBot")

            except Exception as e:
                # Format the exp into a str and remove path prefix
                failed[m] = str(e).replace(f"BoopliBot.{FOLDER_MODULES}.", "")

            else:
                succeed.append(m)

        embed = discord.Embed(title="Reloading modules")

        if succeed:
            embed.add_field(
                name=f"Successfully reloaded the modules ({len(succeed)}/{total_modules}):",
                value="\n".join(map(str_add_dash_space, succeed)),
                inline=False
            )

        else:
            embed.add_field(name="No modules were reloaded", value=EMPTY_EMBED_VALUE, inline=False)

        if failed:
            values = [
                f"{str_add_dash_space(m)} (reason: {failed[m]})"
                for m in failed
            ]
            embed.add_field(
                name=f"Failed to reload the modules ({len(failed)}/{total_modules}):",
                value="\n".join(values),
                inline=False
            )

        if succeed and not failed:
            embed.color = EMB_COLOR_GREEN

        elif failed and not succeed:
            embed.color = EMB_COLOR_RED

        else:
            embed.color = EMB_COLOR_ORANGE

        await ctx.send(embed=embed, reference=ctx.message)

    @commands.command(name="shell", enabled=False)
    @commands.is_owner()
    async def cmd_shell(self, ctx: commands.Context, *, command: str) -> None:
        """
        Executes the given string in shell
        FIXME: this command has been disabled

        IN:
            command - string to execute
        """
        rv = ""
        try:
            async_proc = await asyncio.subprocess.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )
            data_tuple = await async_proc.communicate()
            rv = data_tuple[0].decode("utf-8")

        except Exception as e:
            rv = repr(e)

        finally:
            if len(rv) == 0 or rv.isspace():
                rv = '""'

            await ctx.send(rv, reference=ctx.message)

    @commands.command(name="eval")
    @commands.is_owner()
    async def cmd_eval(self, ctx: commands.Context, *, string: str) -> None:
        """
        Evals the given string

        IN:
            string - the string to eval
        """
        rv = ""
        try:
            string = string.strip(" `")
            string = re.sub(CODE_BLOCK_PATTERN, "", string, count=1).strip("\n ")

            rv = eval(string)

            if isinstance(rv, str):
                rv = f'"{rv}"'
            else:
                rv = str(rv)

            if not rv or rv.isspace():
                rv = '""'

        except Exception as e:
            rv = repr(e)
            # rv = f"Failed ❌\n```{traceback.format_exc()}```"

        finally:
            rv = f"```python\n{rv}\n```"
            await ctx.send(rv, reference=ctx.message)

    @commands.command(name="exec")
    @commands.is_owner()
    async def cmd_exec(self, ctx: commands.Context, *, string: str) -> None:
        """
        Execs the given string

        IN:
            string - the string to exec
        """
        try:
            string = string.strip(" `")
            string = re.sub(CODE_BLOCK_PATTERN, "", string, count=1).strip("\n ")

            exec(string)

        except Exception as e:
            await ctx.send(f"```python\n{repr(e)}\n```", reference=ctx.message)
            # await ctx.send(f"Failed ❌\n```{traceback.format_exc()}```", reference=ctx.message)

        else:
            await ctx.send("✅", reference=ctx.message)


def setup(bot: bot.Bot):
    for cog in _cogs:
        bot.add_cog(cog(bot))

def teardown(bot: bot.Bot):
    for cog in _cogs:
        bot.remove_cog(cog(bot))
