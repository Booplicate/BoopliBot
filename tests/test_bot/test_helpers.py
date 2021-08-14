"""
Module with tests for the helper sub-module
"""

import unittest
# from copy import deepcopy
from itertools import zip_longest


from BoopliBot import helpers


class NestedDictWrapperTest(unittest.TestCase):
    """
    Test case for NestedDictWrapper
    """
    MAX_DEPTH = 9

    def setUp(self) -> None:
        base_data = {
            "foo": "value_foo",
            "bar": "value_bar",
            "__private_key": True,
            "__magick_key__": True,
            "callable_key()": 99,
            "another_key": object(),
            "key_to_dict": dict()
        }
        self.base_data = base_data
        self.ndw = helpers.NestedDictWrapper(base_data, nesting_depth=self.MAX_DEPTH)

    def tearDown(self) -> None:
        try:
            del self.base_data
        except AttributeError:
            pass
        try:
            del self.ndw
        except AttributeError:
            pass

    def test_helpers_ndw_item_in(self) -> None:
        msg = "Case: Expecting keys from the base dict to be in NestedDictWrapper"
        for key in self.base_data.keys():
            with self.subTest(msg):
                self.assertIn(key, self.ndw)

        self.assertNotIn("nonexisting_key", self.ndw)

    def test_helpers_ndw_iter(self) -> None:
        msg = "Case: Expecting keys to match during iteration through the base dict and NestedDictWrapper"
        fillvalue = object()
        for key, valid_key in zip_longest(self.ndw, self.base_data, fillvalue=fillvalue):
            with self.subTest(msg):
                self.assertEqual(key, valid_key)

    def test_helpers_ndw_item_get(self) -> None:
        msg = "Case: Expecting values in the base dict and NestedDictWrapper to match"
        for key, expected_value in self.base_data.items():
            with self.subTest(msg):
                self.assertEqual(self.ndw[key], expected_value)

        msg = "Case: Expecting NestedDictWrapper to return 9 nested instances"
        nonexisting_key = "nonexisting_key"
        nested_dict = self.ndw[nonexisting_key]
        for i in range(self.MAX_DEPTH):
            with self.subTest(msg):
                self.assertIsInstance(nested_dict, helpers.NestedDictWrapper)
                nested_dict = nested_dict[nonexisting_key]

        self.assertIsNone(nested_dict)

    def test_helpers_ndw_item_set(self) -> None:
        new_key = "new_key"
        new_value = "new_value"
        nonexisting_key = "nonexisting_key"
        self.assertNotIn(new_key, self.ndw[nonexisting_key])

        self.ndw[nonexisting_key][new_key] = new_value
        # Added to a temp obj, the key should not be saved
        self.assertNotIn(new_key, self.ndw[nonexisting_key])

        existing_key = "key_to_dict"
        self.assertNotIn(new_key, self.ndw[existing_key])

        self.ndw[existing_key][new_key] = new_value
        # Added to an existing obj, the key should be saved
        self.assertIn(new_key, self.ndw[existing_key])

    def test_helpers_ndw_item_del(self) -> None:
        test_key = "foo"
        self.assertIn(test_key, self.ndw)
        self.assertEqual(self.ndw[test_key], self.base_data[test_key])
        del self.ndw[test_key]
        self.assertNotIn(test_key, self.ndw)
        self.assertNotIn(test_key, self.base_data)
        # This shouldn't raise
        try:
            del self.ndw["can safely delete any key"]

        except KeyError as e:
            self.fail(f"Failed to ignore del of a nonexisting key: {e}")

    def test_helpers_ndw_len(self) -> None:
        self.assertNotEqual(len(self.ndw), 0)
        self.assertEqual(len(self.ndw), len(self.base_data))

    def test_helpers_ndw_bool(self) -> None:
        self.assertTrue(self.ndw)
        self.ndw.clear()
        self.assertFalse(helpers.NestedDictWrapper())

    def test_helpers_ndw_clear(self) -> None:
        self.assertNotEqual(len(self.ndw), 0)
        self.ndw.clear()
        self.assertEqual(len(self.ndw), 0)
        self.assertFalse(self.ndw)

    def test_helpers_ndw_get(self) -> None:
        nonexisting_key = "this_key_doesnt_exist"
        def_value = object()
        self.assertNotIn(nonexisting_key, self.ndw)
        self.assertEqual(self.ndw.get(nonexisting_key, def_value), def_value)
