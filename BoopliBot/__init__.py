"""
BoopliBot - the bot that boops.
"""

from collections import namedtuple
from typing import (
    Tuple
)


import BoopliBot


__title__ = "BoopliBot"
__author__ = "Booplicate"
__version__ = "0.0.2"


VersionInfo = namedtuple("VersionInfo", "major minor micro")


def versionStrToTuple(string: str) -> Tuple[int]:
    """
    Converts version str into a tuple

    IN:
        string - str

    OUT:
        tuple
    """
    return tuple(map(int, string.split(".")))


version_info = VersionInfo(*versionStrToTuple(__version__))
