"""
Module provides main set of commands. This module is required and must always be loaded.
"""

import asyncio
import traceback
import random
import datetime
import time
from typing import (
    Optional
)
import re
import io
import ast
from functools import partial
from inspect import isawaitable
from builtins import print as _print
from pprint import pprint as _pprint


import discord
from discord.ext import commands
import DiscordStatusPy
import psutil


import BoopliBot
from ..bot import Bot
from ..utils import (
    FOLDER_MODULES,
    str_add_dash_space,
    to_code_block,
    from_code_block,
    retrieve_modules,
    register_cog,
    is_owner_or_admin,
    is_owner_or_mod,
    bypass_for_owner_cooldown,
    validate_prefix,
    sql_utils
)
from ..consts import (
    EMB_COLOR_GREEN,
    EMB_COLOR_ORANGE,
    EMB_COLOR_RED,
    EMPTY_EMBED_VALUE,
    ZERO_WIDTH_CHAR
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

    def __init__(self, bot: Bot):
        """
        Constructor

        IN:
            bot - the bot object
        """
        self.bot = bot

    @commands.command(name="ping", aliases=("latency", "statistic", "stats"))
    @commands.max_concurrency(10, wait=True)
    @is_owner_or_mod()
    @commands.dynamic_cooldown(bypass_for_owner_cooldown(rate=1, per=10), type=commands.cooldowns.BucketType.guild)
    async def cmd_ping(self, ctx: commands.Context) -> None:
        """
        Basic ping command
        """
        # Get ws latency
        ws_latency = self.bot.latency * 1000

        # Get bot latency
        start = time.perf_counter()
        await ctx.trigger_typing()
        end = time.perf_counter()
        bot_latency = max(
            (end - start)*1000 - ws_latency,
            0
        )

        # Get db latency
        async with sql_utils.NewAsyncSession() as sesh:
            start = time.perf_counter()
            await sesh.execute(sql_utils.select(1))
            end = time.perf_counter()

            sql_db_latency = (end - start)*1000

        # Get discord status
        disc_status_desc = "No data"
        disc_status_ind = ""
        disc_status_update = ""
        disc_components = "No data"

        async with DiscordStatusPy.APIClient() as api_client:
            api_client: DiscordStatusPy.APIClient
            data = await api_client.get_status()
            try:
                temp_var: str = data["status"]["indicator"]
                if temp_var and temp_var != "none":
                    disc_status_ind = f" ({temp_var})"

                temp_var: str = data["status"]["description"]
                if temp_var:
                    disc_status_desc = temp_var

                temp_var = data["page"]["updated_at"]
                if temp_var:
                    temp_var: str = discord.utils.format_dt(
                        datetime.datetime.fromisoformat(temp_var),
                        "R"
                    )
                    disc_status_update = f" (last updated {temp_var})"

            except KeyError:
                pass

            data = await api_client.get_components()
            try:
                names = {"API", "CloudFlare", "Media Proxy", "Search", "Voice"}
                components = filter(lambda item: item["name"] in names, data["components"])
                parts = list()
                for item in components:
                    name = item["name"]
                    status = "✅" if item["status"] == "operational" else "❌"
                    parts.append(f"- {name} {status}")

                disc_components = "\n".join(parts)

            except KeyError:
                pass

        discord_status = f"{disc_status_desc}{disc_status_ind}:\n{disc_components}"

        # Get process stats
        # mem_stats = psutil.virtual_memory()
        cpu_usage = psutil.cpu_percent()
        # total_mem = mem_stats.total
        # mem_usage = mem_stats.percent
        proc = psutil.Process()
        with proc.oneshot():
            proc.cpu_percent()
            # proc_cpu_usage = proc.cpu_percent()
            # if not proc_cpu_usage:
            #     proc_cpu_usage = 0.1
            proc_mem_usage = proc.memory_percent()
            proc_mem_used = proc.memory_full_info().uss
            runtime_s = int(time.time() - proc.create_time())
            runtime_m = runtime_s // 60
            runtime_h = runtime_m // 60
            runtime_m %= 60
            runtime_d = runtime_h // 24
            runtime_h %= 24

        server_stats = (
            f"Runtime: {runtime_d} Days, {runtime_h} Hours, {runtime_m} Minutes\n"
            f"CPU Usage: {cpu_usage:0.1f}%\n"
            f"Memory Usage: {proc_mem_used / 1024**2:0.0f} MiB ({proc_mem_usage:0.1f}%)"
        )

        embed = discord.Embed()
        embed.add_field(name="Bot Latency:", value=f"{bot_latency:0.0f} ms", inline=False)
        embed.add_field(name="WS Latency:", value=f"{ws_latency:0.0f} ms", inline=False)
        embed.add_field(name="SQL DB Latency:", value=f"{sql_db_latency:0.0f} ms", inline=False)
        embed.add_field(name=f"Discord Status{disc_status_update}:", value=discord_status, inline=False)
        embed.add_field(name="Bot Status:", value=server_stats, inline=False)

        if (
            bot_latency <= 50
            and ws_latency <= 150
            and sql_db_latency <= 50
        ):
            color = EMB_COLOR_GREEN

        elif (
            bot_latency <= 100
            and ws_latency <= 300
            and sql_db_latency <= 100
        ):
            color = EMB_COLOR_ORANGE

        else:
            color = EMB_COLOR_RED
        embed.color = color

        await ctx.send(embed=embed, reference=ctx.message)

    @commands.command(name="prefix")
    @is_owner_or_admin()
    @commands.guild_only()
    async def cmd_prefix(self, ctx: commands.Context, new_prefix: Optional[str] = None) -> None:
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
    @commands.max_concurrency(1)
    @commands.is_owner()
    async def cmd_activity(self, ctx: commands.Context, *, string: Optional[str] = None) -> None:
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
            activity = Bot.DEF_ACTIVITY
            self.bot.config.activity_text = ""

        await asyncio.to_thread(self.bot.config.save_if_dirty)
        await self.bot.change_presence(activity=activity)

    @commands.command(name="shutdown", aliases=("die", "kill", "slep", "sleep"))
    @commands.is_owner()
    async def cmd_shutdown(self, ctx: commands.Context) -> None:
        """
        Shutdowns the bot
        """
        self.bot.exit_code = Bot.EXIT_CODE_QUIT
        await ctx.channel.send(random.choice(RootCommands.GOODBYE_MESSAGES), reference=ctx.message)
        await self.bot.close()

    @commands.command(name="restart", aliases=("reload", "reboot"))
    @commands.is_owner()
    async def cmd_restart(self, ctx: commands.Context) -> None:
        """
        Restarts the bot
        """
        self.bot.exit_code = Bot.EXIT_CODE_RESTART
        await ctx.channel.send("Restarting...", reference=ctx.message)
        await self.bot.close()

    @commands.command(name="maintenance", aliases=("service", "serv"))
    @commands.is_owner()
    async def cmd_toggle_maintenance(self, ctx: commands.Context, flag: bool) -> None:
        """
        Toggles maintenance mode

        IN:
            flag - boolean
        """
        if self.bot.is_in_maintenance is not flag:
            self.bot.is_in_maintenance = flag
            if flag:
                msg = "Turned on maintenance mode."

            else:
                msg = "Turned off maintenance mode."

        else:
            if flag:
                msg = "Already in maintenance mode."

            else:
                msg = "Already not in maintenance mode."

        await ctx.channel.send(msg, reference=ctx.message)

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
        string = from_code_block(string)
        try:
            code = compile(string, "<string>", "eval", flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
            result = eval(code)
            if isawaitable(result):
                output = await result

            else:
                output = result

            if isinstance(output, str):
                output = f'"{output}"'
            else:
                output = str(output)

            if not output:
                output = ZERO_WIDTH_CHAR

        except Exception as e:
            status = "Failure❌"
            output = repr(e)
            # traceback.format_exc()

        else:
            status = "Success✅"

        finally:
            msg = f"{status}\n{to_code_block(output)}"
            await ctx.send(msg, reference=ctx.message)

    @commands.command(name="exec")
    @commands.is_owner()
    async def cmd_exec(self, ctx: commands.Context, *, string: str) -> None:
        """
        Execs the given string
        NOTE: internally defines a buffer for redirecting stdout

        IN:
            string - the string to exec
        """
        buffer = io.StringIO()
        print = partial(_print, file=buffer)
        pprint = partial(_pprint, stream=buffer, indent=1, depth=3, width=40, compact=True)

        string = from_code_block(string)
        try:
            code = compile(string, "<string>", "exec", flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)
            result = eval(code)
            if isawaitable(result):
                await result

        except Exception as e:
            status = "Failure❌"
            output = repr(e)
            # traceback.format_exc()

        else:
            status = "Success✅"
            output = buffer.getvalue().strip("\n")

        finally:
            buffer.close()
            msg = "{status}{newline}{output}".format(
                status=status,
                newline="\n" if output else "",
                output=to_code_block(output) if output else ""
            )
            await ctx.send(msg, reference=ctx.message)


def setup(bot: Bot):
    for cog in _cogs:
        bot.add_cog(cog(bot))

def teardown(bot: Bot):
    for cog in _cogs:
        bot.remove_cog(cog(bot))
