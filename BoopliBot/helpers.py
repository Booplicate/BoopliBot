"""
This modules contains constants extra classes.
"""

# from collections import namedtuple
from collections.abc import (
    Hashable,
    Iterator,
    KeysView,
    ValuesView,
    ItemsView
)
from typing import (
    Any,
    Optional,
    Union,
    NamedTuple
)


import discord


# PartialAuditLogEntry = namedtuple("PartialAuditLogEntry", ("action", "user", "target", "reason"))
class PartialAuditLogEntry(NamedTuple):
    """
    Represents partial log entry for use in custom discord events
    """
    action: str
    user: discord.Member
    target: Union[discord.Member, discord.User]
    reason: Optional[str]

class NestedDictWrapper():
    """
    A wrapper to safely recursively access dict-like objects.
    NOTE:
        Does not have the full set of dict methods implemented
        Adding a new key to a nested dict will have no effect as new dicts are created temporary:
            >>> d.foo.bar = 5
            >>> d.foo.bar == 5
            False
        Allows access dict items via attributes:
            >>> d['key'] is d.key
            True
    """
    __slots__ = ("__data", "__nesting_depth", "__default_value")

    def __init__(self, data: Optional[dict] = None, *, nesting_depth: int = -1, default_value: Any = None) -> None:
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
        return (
            f"{type(self).__name__}("
            f"{self.__data}, "
            f"nesting_depth={self.__nesting_depth}, "
            f"default_value={self.__default_value}"
            ")"
        )

    def __contains__(self, key: Hashable) -> bool:
        """
        Override for __contains__
        """
        return key in self.__data

    def __len__(self) -> int:
        """
        Override for the len magic method

        OUT:
            boolean
        """
        return len(self.__data)

    def __bool__(self) -> bool:
        """
        Override for the bool magic method

        OUT:
            boolean
        """
        return bool(self.__data)

    def __iter__(self) -> Iterator:
        """
        Override for the iter magic method

        OUT:
            iterator over inner dict keys
        """
        for key in self.__data:
            yield key

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
        if name not in self:
            depth = self.__nesting_depth
            if depth != 0:
                if depth > 0:
                    depth -= 1
                return type(self)(nesting_depth=depth, default_value=self.__default_value)

            return self.__default_value

        return self.__data[name]

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
        if key in self:
            del self.__data[key]

    def __getattr__(self, name: str) -> Any:
        """
        Override for attribute getter

        IN:
            name - the attr
        """
        return self[name]

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
            self[name] = value

    def __delattr__(self, name: str) -> None:
        """
        Override for attribute deletter

        IN:
            name - the attr
        """
        del self[name]

    def get(self, key: Hashable, default: Any = None) -> Any:
        """
        Implementation of the dict get method

        IN:
            key - the key to access
            default - the default value to return

        OUT:
            key value or default
        """
        if key in self:
            return self[key]

        return default

    def keys(self) -> KeysView:
        """
        Implementation of the dict keys method

        OUT:
            view object
        """
        return self.__data.keys()

    def values(self) -> ValuesView:
        """
        Implementation of the dict values method

        OUT:
            view object
        """
        return self.__data.values()

    def items(self) -> ItemsView:
        """
        Implementation of the dict items method

        OUT:
            view object
        """
        return self.__data.items()

    def clear(self) -> None:
        """
        Implementation of the dict clear method
        """
        return self.__data.clear()
