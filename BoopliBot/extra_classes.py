"""
This modules contains constants extra classes.
"""

from collections import namedtuple
from typing import (
    Any,
    Hashable,
)


import discord


# Represents partial log entry for use in custom discord events
PartialAuditLogEntry = namedtuple("PartialAuditLogEntry", "action user target reason")

class NestedDictWrapper():
    """
    A wrapper to safely access dicts of nested dicts of nested dicts of...

    Also allows to access dict items as attributes
    """
    __slots__ = ("__data", "__nesting_depth", "__default_value")

    def __init__(self, data: dict = None, *, nesting_depth: int = -1, default_value: Any = None) -> None:
        """
        Constructor

        IN:
            data - dict data
                NOTE: make sure you deepcopy it before passing in, if needed
            nesting_depth - maximum nesting depth; -1 means unlimited
                (Default: -1)
            default_value - the value to return when we reach the nesting limit
                (Default: None)
        """
        self.__data = data if data is not None else dict()
        self.__nesting_depth = max(-1, nesting_depth)
        self.__default_value = default_value

    def __repr__(self) -> str:
        """
        Repr override
        """
        return f"{type(self).__name__}({self.__data}, nesting_depth={self.__nesting_depth}, default_value={self.__default_value})"

    def __unmangle_attr_name(self, name: str) -> str:
        """
        Removes the extra part from the attribute name

        IN:
            name - the attr name

        OUT:
            str
        """
        return name.replace(f"_{type(self).__name__}", "")

    def __value_or_safedict(self, name: Hashable) -> Any:
        """
        Returns the value for the given key, or a new SafeDict as a fallback

        IN:
            name - the key

        OUT:
            stored value or new SafeDict
        """
        if name not in self.__data:
            depth = self.__nesting_depth
            if depth != 0:
                if depth > 0:
                    depth -= 1
                return type(self)(nesting_depth=depth, default_value=self.__default_value)

            return self.__default_value

        return self.__data[name]

    def __getattr__(self, name: str) -> Any:
        """
        Override for attribute getter

        IN:
            name - the attr
        """
        return self.__value_or_safedict(name)

    def __setattr__(self, name: str, value: Any) -> None:
        """
        Override for attribute setter

        IN:
            name - the attr
            value - the value
        """
        if self.__unmangle_attr_name(name) in type(self).__slots__:
            super().__setattr__(name, value)

        else:
            self.__data[name] = value

    def __delattr__(self, name: str) -> None:
        """
        Override for attribute deletter

        IN:
            name - the attr
        """
        if name in self.__data:
            del self.__data[name]

    def get(self, key: Hashable, default: Any = None) -> Any:
        """
        Implementation of dict get method

        IN:
            key - the key to access
            default - the default value to return

        OUT:
            value or default
        """
        if key in self:
            return self[key]

        return default

    def __getitem__(self, key: Hashable) -> Any:
        """
        Override for item getter
        """
        return self.__value_or_safedict(key)

    def __setitem__(self, key: Hashable, value: Any) -> None:
        """
        Override for item setter
        """
        self.__data[key] = value

    def __delitem__(self, key: Hashable) -> None:
        """
        Override for item deletter
        """
        if key in self.__data:
            del self.__data[key]

    def __contains__(self, key: Hashable) -> bool:
        """
        Override for __contains__
        """
        return key in self.__data
