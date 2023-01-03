"""
Sub-module with custom mocks
"""

import unittest


import discord


GUILD_DATA = {
    "afk_channel_id": None,
    "afk_timeout": 300,
    "application_command_count": 0,
    "application_command_counts": {"1": 0, "2": 0, "3": 0},
    "application_id": None,
    "banner": None,
    "default_message_notifications": 1,
    "description": None,
    "discovery_splash": None,
    "explicit_content_filter": 0,
    "features": [],
    "icon": None,
    "id": "52371571028787200",
    "joined_at": "2015-05-25T12:25:55.550000+00:00",
    "large": False,
    "lazy": True,
    "max_members": 250000,
    "max_video_channel_users": 25,
    "member_count": 15,
    "mfa_level": 0,
    "name": "Sample Guild",
    "nsfw": False,
    "nsfw_level": 0,
    "owner_id": "647602717296164864",
    "preferred_locale": "en-US",
    "premium_subscription_count": 0,
    "premium_tier": 0,
    "public_updates_channel_id": None,
    "region": "europe",
    "rules_channel_id": None,
    "splash": None,
    "stage_instances": [],
    "stickers": [],
    "system_channel_flags": 0,
    "system_channel_id": None,
    "threads": [],
    "unavailable": False,
    "vanity_url_code": None,
    "verification_level": 1,
    "voice_states": []
}
sample_guild = discord.Guild(data=GUILD_DATA, state=unittest.mock.NonCallableMagicMock())
