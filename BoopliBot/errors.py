"""
Module that contains custom exceptions for BoopliBot
"""

import discord
from discord.ext import commands


class BadConfig(Exception):
    """
    Raised when used wrong configuration options
    """
    pass
    # def __init__(self, msg: str) -> None:
    #     super().__init__()
    #     self.msg = msg

    # def __str__(self) -> str:
    #     return self.msg

    # def __repr__(self) -> str:
    #     return f"{type(self).__name__}({self.msg})"

class BadBotPrefix(Exception):
    """
    Raised when the bot prefix is improper
    """
    pass


class MissingRequiredSubCommand(commands.UserInputError):
    """
    Exception raised when a command is missing subcommands
    """
    pass

class MissingPermissionsAndNotOnSelf(commands.CheckFailure):
    """
    Exception raised when a command is being used by a user w/o
    required permissions and not on oneself
    """
    pass

class TooLowInHierarchy(commands.CheckFailure):
    """
    Exception raised when a command is being used by a user who
    is lower in the server hierarchy than the targeted user
    """
    pass

class BotTooLowInHierarchy(commands.CheckFailure):
    """
    Exception raised when a command is being used by a user who
    is lower in the server hierarchy than the targeted user
    """
    pass

class BadRole(commands.BadArgument):
    """
    Exception raised when a role cannot be used in the command
    """
    def __init__(self, argument: discord.Role):
        self.argument = argument
        super().__init__(f"Role {discord.utils.escape_mentions(argument.name)} cannot be used in this command.")

class BotAlreadyExists(Exception):
    """
    Exception raised when attemp to define a bot when one has been alredy defined
    """
    MSG = "A BoopliBot has already been initialised."

    def __str__(self):
        return BotAlreadyExists.MSG

class MemberOrUserNotFound(commands.BadArgument):
    """
    Exception raised when an argument couldn't be converted into a discord member/user
    """
    def __init__(self, argument):
        self.argument = argument
        super().__init__(f"Couldn't convert {argument} into a discord member/user.")
