"""
Modules with tests for the sql system
"""

import unittest
from unittest.mock import patch
from typing import (
    List
)


from BoopliBot.utils import sql_utils


patchers: List[unittest.mock._patch] = list()

def setUpModule() -> None:
    # Setup in-memory sqlite3 db
    const_to_patch = {
        "BoopliBot.utils.sql_utils.ENGINE_URL": "sqlite://",
        "BoopliBot.utils.sql_utils.ENGINE_URL_ASYNC": "sqlite+aiosqlite://",
    }
    for const, new_value in const_to_patch.items():
        p = patch(const, new_value)
        patchers.append(p)
        p.start()

def tearDownModule() -> None:
    # Remove patches
    for p in patchers:
        p.stop()

class SQLTest(unittest.TestCase):
    """
    Test case for config_utils.sql_utils
    """
    def setUp(self) -> None:
        sql_utils.metadata.create_all(sql_utils.engine)

    def tearDown(self) -> None:
        sql_utils.metadata.drop_all(sql_utils.engine)

    @classmethod
    def setUpClass(cls) -> None:
        sql_utils.init(should_log=False)

    @classmethod
    def tearDownClass(cls) -> None:
        sql_utils.deinit(should_log=False)

    def test_sql_guild_config_create(self) -> None:
        test_guild_id = 999999999
        test_prefix = "!"

        with sql_utils.NewSession() as sesh:
            nonexisting_guild = sesh.get(sql_utils.GuildConfig, test_guild_id)

            self.assertIsNone(nonexisting_guild)

            new_guild = sql_utils.GuildConfig(guild_id=test_guild_id, prefix=test_prefix)
            sesh.add(new_guild)
            sesh.commit()
            existing_guild = sesh.get(sql_utils.GuildConfig, test_guild_id)

            # This should be disabled by default
            self.assertFalse(new_guild.enable_cc)
            # These 3 are None by default
            self.assertIsNone(new_guild.log_channel)
            self.assertIsNone(new_guild.welcome_channel)
            self.assertIsNone(new_guild.system_channel)

            self.assertEqual(new_guild, existing_guild)

            sesh.delete(existing_guild)
            sesh.commit()
            deleted_guild = sesh.get(sql_utils.GuildConfig, test_guild_id)
            self.assertIsNone(deleted_guild)

    def test_sql_guild_config_update(self) -> None:
        test_guild_id = 999999999
        test_prefix = "!"

        with sql_utils.NewSession() as sesh:
            guild = sql_utils.GuildConfig(guild_id=test_guild_id, prefix=test_prefix)
            sesh.add(guild)
            sesh.commit()

            self.assertEqual(guild.prefix, test_prefix)

            new_prefix = "$"
            guild.prefix = new_prefix
            sesh.commit()
            self.assertEqual(guild.prefix, new_prefix)

    def test_sql_user_create(self) -> None:
        test_guild_id = 999999999
        test_user_id = 555555555

        with sql_utils.NewSession() as sesh:
            nonexisting_user = sesh.get(sql_utils.User, (test_guild_id, test_user_id))

            self.assertIsNone(nonexisting_user)

            new_user = sql_utils.User(guild_id=test_guild_id, user_id=test_user_id)
            sesh.add(new_user)
            sesh.commit()
            existing_user = sesh.get(sql_utils.User, (test_guild_id, test_user_id))

            # These default to 0s
            self.assertEqual(new_user.current_warns, 0)
            self.assertEqual(new_user.total_warns, 0)
            self.assertEqual(new_user.total_kicks, 0)
            self.assertEqual(new_user.total_bans, 0)

            self.assertEqual(new_user, existing_user)

            sesh.delete(existing_user)
            sesh.commit()
            deleted_user = sesh.get(sql_utils.User, (test_guild_id, test_user_id))
            self.assertIsNone(deleted_user)

    def test_sql_user_update(self) -> None:
        test_guild_id = 999999999
        test_user_id = 555555555

        with sql_utils.NewSession() as sesh:
            user = sql_utils.User(guild_id=test_guild_id, user_id=test_user_id)
            sesh.add(user)
            sesh.commit()

            self.assertEqual(user.total_bans, 0)

            new_bans = 5
            user.total_bans = new_bans
            sesh.commit()

            self.assertEqual(user.total_bans, new_bans)

    def test_sql_update(self) -> None:
        test_guild_id = 999999999
        test_user_id = 555555555

        with sql_utils.NewSession() as sesh:
            user_one = sql_utils.User(guild_id=test_guild_id, user_id=test_user_id)
            user_two = sql_utils.User(guild_id=test_guild_id, user_id=test_user_id-5)
            user_three = sql_utils.User(guild_id=test_guild_id, user_id=test_user_id-10)
            user_four = sql_utils.User(guild_id=test_guild_id-5, user_id=test_user_id-15)
            sesh.add_all(
                (user_one, user_two, user_three, user_four)
            )
            sesh.commit()

            new_warns = 9
            # Update only 3 of 4
            stmt = (
                sql_utils.update(sql_utils.User)
                .values(current_warns=new_warns)
                .where(sql_utils.User.guild_id == test_guild_id)
            )
            sesh.execute(stmt)
            sesh.commit()

            stmt = (
                sql_utils.select(sql_utils.User)
                .where(sql_utils.User.current_warns == new_warns)
            )
            result_list = sesh.execute(stmt).scalars().all()
            self.assertIn(user_one, result_list)
            self.assertIn(user_two, result_list)
            self.assertIn(user_three, result_list)
            # This one hasn't been updated
            self.assertNotIn(user_four, result_list)

            new_warns = 15
            # Update everyone
            stmt = (
                sql_utils.update(sql_utils.User)
                .values(current_warns=new_warns)
                .where(sql_utils.User.current_warns < new_warns)
            )
            sesh.execute(stmt)
            sesh.commit()

            self.assertEqual(user_two.current_warns, new_warns)
            self.assertEqual(user_four.current_warns, new_warns)
