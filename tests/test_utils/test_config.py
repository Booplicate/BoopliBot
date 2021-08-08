"""
Modules with tests for the config system
"""

import unittest
import os

from BoopliBot.utils import config_utils


THIS_FOLDER = os.path.dirname(os.path.realpath(os.path.abspath(__file__)))

def setUpModule() -> None:
    pass

def tearDownModule() -> None:
    pass

class ConfigTest(unittest.TestCase):
    """
    Test case for config_utils.Config
    """
    FP_CONFIG_VALID = os.path.join(THIS_FOLDER, "fixtures/config_valid.json")
    FP_CONFIG_BAD_PREFIX = os.path.join(THIS_FOLDER, "fixtures/config_bad_prefix.json")
    FP_CONFIG_DOUBLE_OWNER_FIELD = os.path.join(THIS_FOLDER, "fixtures/config_double_owner_field.json")
    FP_CONFIG_EXTRA_FIELD = os.path.join(THIS_FOLDER, "fixtures/config_extra_field.json")
    FP_CONFIG_MISSING_REQ_FIELD = os.path.join(THIS_FOLDER, "fixtures/config_missing_token.json")

    def setUp(self) -> None:
        pass

    def tearDown(self) -> None:
        pass

    @classmethod
    def setUpClass(cls) -> None:
        pass

    @classmethod
    def tearDownClass(cls) -> None:
        pass

    def test_config_valid(self) -> None:
        try:
            config_utils.Config(self.FP_CONFIG_VALID)

        except config_utils.BadConfig as e:
            self.fail(str(e))

    def test_config_invalid(self) -> None:
        test_cases = (
            ("Case: invalid bot prefix", self.FP_CONFIG_BAD_PREFIX),
            ("Case: json has both owner_id and owner_ids", self.FP_CONFIG_DOUBLE_OWNER_FIELD),
            ("Case: json has an extra field", self.FP_CONFIG_EXTRA_FIELD),
            ("Case: json is missing a requared field", self.FP_CONFIG_MISSING_REQ_FIELD)
        )

        for msg, json_fp in test_cases:
            with self.subTest(msg=msg, json_fp=json_fp):
                with self.assertRaises(config_utils.BadConfig):
                    config_utils.Config(json_fp)

    def test_config_attr_get(self) -> None:
        config = config_utils.Config(self.FP_CONFIG_VALID)
        data = config.to_dict()

        self.assertEqual(config.token, data["token"])
        self.assertEqual(config.def_prefix, data["def_prefix"])
        self.assertEqual(config.shard_count, data["shard_count"])

    def test_config_attr_set(self) -> None:
        config = config_utils.Config(self.FP_CONFIG_VALID)
        data = config.to_dict()
        new_token = "new_token_value"

        # Set to the same value we have in the dict
        # It should NOT be dirty
        config.token = data["token"]
        self.assertFalse(config.is_dirty())

        # Now we change the field for real
        # It SHOULD be dirty
        config.token = new_token
        self.assertTrue(config.is_dirty())
        self.assertEqual(config.token, new_token)

        # Can't set random attributes
        with self.assertRaises(AttributeError):
            config.this_doesnt_exist = None

    def test_config_attr_del(self) -> None:
        config = config_utils.Config(self.FP_CONFIG_VALID)

        with self.assertRaises(AttributeError):
            del config.token

        with self.assertRaises(AttributeError):
            del config.case_insensitive

        with self.assertRaises(AttributeError):
            del config.this_doesnt_exist
