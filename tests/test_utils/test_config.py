"""
Modules with tests for the config system
"""

import unittest
import os
import json
from typing import (
    Any
)

from BoopliBot.utils import config_utils


THIS_FOLDER = os.path.dirname(os.path.realpath(os.path.abspath(__file__)))


class _Mixin():
    FP_CONFIG_VALID = os.path.join(THIS_FOLDER, "fixtures/config_valid.json")
    FP_CONFIG_BAD_PREFIX = os.path.join(THIS_FOLDER, "fixtures/config_bad_prefix.json")
    FP_CONFIG_DOUBLE_OWNER_FIELD = os.path.join(THIS_FOLDER, "fixtures/config_double_owner_field.json")
    FP_CONFIG_EXTRA_FIELD = os.path.join(THIS_FOLDER, "fixtures/config_extra_field.json")
    FP_CONFIG_MISSING_REQ_FIELD = os.path.join(THIS_FOLDER, "fixtures/config_missing_token.json")

class ConfigInitTest(unittest.TestCase, _Mixin):
    """
    Test case for config_utils.Config
    """
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

class ConfigAttributesTest(unittest.TestCase, _Mixin):
    """
    Test case for config_utils.Config
    """
    def setUp(self) -> None:
        self.config = config_utils.Config(self.FP_CONFIG_VALID)
        with open(self.FP_CONFIG_VALID, "r") as json_file:
            self.json_data: dict[str, Any] = json.load(json_file)

    def tearDown(self) -> None:
        try:
            del self.config
        except:
            pass
        try:
            del self.json_data
        except:
            pass

    def test_config_attr_get(self) -> None:
        config = self.config
        json_data = self.json_data
        def_value = object()
        msg = "Case: Expecting config values to match values from the original dict"

        for key, expected_value in json_data.items():
            with self.subTest(msg):
                config_value = getattr(config, key, def_value)
                self.assertEqual(config_value, expected_value)

        self.assertEqual(config.token, json_data["token"])
        with self.assertRaises(AttributeError):
            config.non_existing_attr

    def test_config_attr_set(self) -> None:
        config = self.config
        json_data = self.json_data
        new_token = "new_token_value"

        # Set to the same value we have in the dict
        # It should NOT be dirty
        config.token = json_data["token"]
        self.assertEqual(config.token, json_data["token"])
        self.assertFalse(config.is_dirty())

        # Now we change the field for real
        # It SHOULD be dirty
        config.token = new_token
        self.assertEqual(config.token, new_token)
        self.assertTrue(config.is_dirty())

        # Can't set random attributes
        with self.assertRaises(AttributeError):
            config.this_doesnt_exist = None

    def test_config_attr_del(self) -> None:
        config = self.config

        with self.assertRaises(AttributeError):
            del config.token

        with self.assertRaises(AttributeError):
            del config.case_insensitive

        with self.assertRaises(AttributeError):
            del config.this_doesnt_exist

    def test_config_to_dict(self) -> None:
        config_dict = self.config.to_dict()
        self.assertEqual(config_dict, self.json_data)

    def test_config_from_dict(self) -> None:
        config = self.config
        test_dict = {
            "token": "new_token_value",
            "strip_after_prefix": not config.strip_after_prefix
        }
        config.from_dict(test_dict)
        def_value = object()
        msg = "Case: Expecting config values to match values from the test dict"

        for key, expected_value in test_dict.items():
            with self.subTest(msg):
                config_value = getattr(config, key, def_value)
                self.assertEqual(config_value, expected_value)
