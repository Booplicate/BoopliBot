"""
Modules implements config for BoopliBot
"""

import os
import logging
import json
from copy import deepcopy
from typing import (
    Any,
    NoReturn
)


from ..errors import BadConfig


CONFIG_FILE = "config.json"

logger = logging.getLogger(__name__)
bot_config = None

class Config:
    """
    A class to represent bot config. NOT thread-safe.
    """
    __REQUIRED_SETTINGS = (
        "token",
        "def_prefix",
        "shard_count"
    )
    __SUPPORTED_SETTINGS = (
        "owner_id",
        "owner_ids",
        "activity_text",
        "description",
        "case_insensitive",
        "strip_after_prefix"
    )
    __ALL_SETTINGS = __REQUIRED_SETTINGS + __SUPPORTED_SETTINGS
    __OTHER_ATTRS = (
        "config_fp",
        "__settings",
        "__dirty"
    )
    __slots__ = __ALL_SETTINGS + __OTHER_ATTRS

    def __init__(self, config_fp: str) -> None:
        """
        Constructor

        IN:
            config_fp - the filepath to the config json
        """
        self.config_fp = config_fp

        with open(config_fp, "r") as settings_json:
            settings: dict = json.load(settings_json)
        self.__validate_settings(settings)

        self.__settings = settings
        self.__dirty = False

    def __repr__(self) -> str:
        """
        Repr override
        """
        settings = str(self.__settings).replace(self.__settings["token"], "[...]")
        return f"{type(self).__name__}({settings})"

    @staticmethod
    def __validate_settings(settings: dict) -> None:
        """
        Validates the given settings, raises an exception if something is wrong,
        may mutate the given dict in a way.

        IN:
            settings - dict with settings
        """
        # Handle owners (we can have only one of these params, and better to have owner_ids as a set)
        if "owner_ids" in settings:
            if "owner_id" in settings:
                raise BadConfig("Two mutually exclusive config settings are used at once: 'owner_id' and 'owner_ids'.")

            settings["owner_ids"] = set(settings["owner_ids"])

        # Make sure our settings are valid
        req_settings = set(Config.__REQUIRED_SETTINGS)
        sup_settings = set(Config.__SUPPORTED_SETTINGS)
        for key in settings:
            if key in req_settings:
                req_settings.remove(key)

            elif key not in sup_settings:
                raise BadConfig(f"Unknown config setting '{key}'.")

        if req_settings:
            raise BadConfig("Missing required config settings: {0}.".format(", ".join(req_settings)))

        # TODO: add more as needed

    def __getattr__(self, name: str) -> Any:
        """
        Override for attribute getter
        """
        if name in Config.__ALL_SETTINGS:
            return self.__settings.get(name, None)

        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def __setattr__(self, name: str, value: Any) -> None:
        """
        Override for attribute setter
        """
        if name in Config.__ALL_SETTINGS:
            if name not in self.__settings or self.__settings[name] != value:
                self.__dirty = True
            self.__settings[name] = value

        else:
            super().__setattr__(name, value)

    def __delattr__(self, name: str) -> NoReturn:
        """
        Override for attribute deletter
        """
        # Try to AttributeError
        getattr(self, name)

        raise AttributeError(f"'{type(self).__name__}' object does not support attribute deletion")

    def to_dict(self) -> dict:
        """
        Returns a new dict with bot config

        OUT:
            dict
        """
        return deepcopy(self.__settings)

    def from_dict(self, data: dict) -> None:
        """
        Updates config using the given dict

        IN:
            data - doct with config data
        """
        data = deepcopy(data)
        self.__settings.update(data)
        self.__dirty = True

    def save(self) -> None:
        """
        Saves config
        """
        with open(self.config_fp, "w") as settings_json:
            json.dump(self.__settings, settings_json, indent=4)
            self.__dirty = False

    def save_if_dirty(self) -> None:
        """
        Updates config file on disk if needed
        """
        if self.__dirty:
            self.save()


def init():
    """
    Inits bot config
    """
    global bot_config

    bot_config = Config(os.path.join(os.getcwd(), CONFIG_FILE))
    logger.info("Config inited.")

def deinit() -> None:
    """
    Deinits bot config
    """
    bot_config.save_if_dirty()
    logger.info("Config deinited.")
