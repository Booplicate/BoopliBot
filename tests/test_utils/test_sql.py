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
    TEST_GUILD_ID = 626871007185207297
    TEST_PREFIX = "!"
    TEST_USER_ID = 647602717296164864

    def setUp(self) -> None:
        sql_utils.metadata.create_all(sql_utils.engine)

        with sql_utils.NewSession() as sesh:
            test_user = sql_utils.User(guild_id=self.TEST_GUILD_ID, user_id=self.TEST_USER_ID)
            test_guild = sql_utils.GuildConfig(guild_id=self.TEST_GUILD_ID, prefix=self.TEST_PREFIX)
            sesh.add_all((test_user, test_guild))
            sesh.commit()

    def tearDown(self) -> None:
        sql_utils.metadata.drop_all(sql_utils.engine)

    @classmethod
    def setUpClass(cls) -> None:
        sql_utils.init(should_log=False)

    @classmethod
    def tearDownClass(cls) -> None:
        sql_utils.deinit(should_log=False)

    def test_sql_guild_config_create(self) -> None:
        with sql_utils.NewSession() as sesh:
            test_guild_id = self.TEST_GUILD_ID + 5

            nonexisting_guild = sesh.get(sql_utils.GuildConfig, test_guild_id)

            self.assertIsNone(nonexisting_guild)

            new_guild = sql_utils.GuildConfig(guild_id=test_guild_id, prefix=self.TEST_PREFIX)
            sesh.add(new_guild)
            sesh.commit()
            existing_guild = sesh.get(sql_utils.GuildConfig, test_guild_id)

            self.assertEqual(new_guild, existing_guild)

            # This should be disabled by default
            self.assertFalse(new_guild.enable_cc)
            # These 3 are None by default
            self.assertIsNone(new_guild.log_channel)
            self.assertIsNone(new_guild.welcome_channel)
            self.assertIsNone(new_guild.system_channel)

    def test_sql_guild_config_delete(self) -> None:
        with sql_utils.NewSession() as sesh:
            test_guild = sesh.get(sql_utils.GuildConfig, self.TEST_GUILD_ID)
            # Obv this cannot be None
            self.assertIsNotNone(test_guild)

            sesh.delete(test_guild)
            sesh.commit()

            deleted_guild = sesh.get(sql_utils.GuildConfig, self.TEST_GUILD_ID)
            self.assertIsNone(deleted_guild)

    def test_sql_guild_config_update(self) -> None:
        with sql_utils.NewSession() as sesh:
            test_guild = sesh.get(sql_utils.GuildConfig, self.TEST_GUILD_ID)

            self.assertEqual(test_guild.prefix, self.TEST_PREFIX)

            new_prefix = "$"
            test_guild.prefix = new_prefix
            sesh.commit()
            self.assertEqual(test_guild.prefix, new_prefix)

    def test_sql_user_create(self) -> None:
        with sql_utils.NewSession() as sesh:
            test_guild_id = self.TEST_GUILD_ID - 5
            test_user_id = self.TEST_USER_ID + 5
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

    def test_sql_user_delete(self) -> None:
        with sql_utils.NewSession() as sesh:
            test_user = sesh.get(sql_utils.User, (self.TEST_GUILD_ID, self.TEST_USER_ID))
            self.assertIsNotNone(test_user)

            sesh.delete(test_user)
            sesh.commit()

            deleted_user = sesh.get(sql_utils.User, (self.TEST_GUILD_ID, self.TEST_USER_ID))
            self.assertIsNone(deleted_user)

    def test_sql_user_update(self) -> None:
        with sql_utils.NewSession() as sesh:
            test_user = sesh.get(sql_utils.User, (self.TEST_GUILD_ID, self.TEST_USER_ID))

            self.assertEqual(test_user.total_bans, 0)

            new_bans = 5
            test_user.total_bans = new_bans
            sesh.commit()

            self.assertEqual(test_user.total_bans, new_bans)

    def test_sql_bulk_update(self) -> None:
        with sql_utils.NewSession() as sesh:
            user_one = sql_utils.User(guild_id=self.TEST_GUILD_ID, user_id=self.TEST_USER_ID - 5)
            user_two = sql_utils.User(guild_id=self.TEST_GUILD_ID, user_id=self.TEST_USER_ID - 10)
            user_three = sql_utils.User(guild_id=self.TEST_GUILD_ID, user_id=self.TEST_USER_ID - 15)
            # This one has different guild_id
            user_four = sql_utils.User(guild_id=self.TEST_GUILD_ID - 5, user_id=self.TEST_USER_ID - 20)

            sesh.add_all(
                (user_one, user_two, user_three, user_four)
            )
            sesh.commit()

            new_warns = 9
            # Update only 3 of 4
            stmt = (
                sql_utils.update(sql_utils.User)
                .values(current_warns=new_warns)
                .where(sql_utils.User.guild_id == self.TEST_GUILD_ID)
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

    def test_sql_bulk_select(self) -> None:
        with sql_utils.NewSession() as sesh:
            stmt = (
                sql_utils.select(sql_utils.User)
                .where(sql_utils.User.user_id == self.TEST_USER_ID and sql_utils.User.guild_id == self.TEST_GUILD_ID)
                .limit(5)
                .offset(0)
            )
            rv = sesh.execute(stmt).scalars().all()
            self.assertEqual(len(rv), 1)
            user: sql_utils.User = rv[0]
            self.assertEqual(user.user_id, self.TEST_USER_ID)
            self.assertEqual(user.guild_id, self.TEST_GUILD_ID)

    def test_sql_bulk_delete(self) -> None:
        with sql_utils.NewSession() as sesh:
            test_user = sesh.get(sql_utils.User, (self.TEST_GUILD_ID, self.TEST_USER_ID))
            self.assertIsNotNone(test_user)

            stmt = (
                sql_utils.delete(sql_utils.User)
                .where(sql_utils.User.guild_id == self.TEST_GUILD_ID)
            )
            sesh.execute(stmt)
            sesh.commit()
            test_user = sesh.get(sql_utils.User, (self.TEST_GUILD_ID, self.TEST_USER_ID))

            self.assertIsNone(test_user)
