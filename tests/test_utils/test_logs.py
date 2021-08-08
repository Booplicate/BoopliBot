"""
Modules with tests for the logging system
"""

import unittest
from unittest.mock import patch
import logging
import threading
from collections import Counter

from BoopliBot.utils import log_utils


def setUpModule() -> None:
    pass

def tearDownModule() -> None:
    pass

class LogsTest(unittest.TestCase):
    """
    Test case for config_utils.log_utils
    """
    # Tuples of the (level, msg) format
    TEST_CASES = (
        (logging.INFO, "TEST INFO MSG"),
        (logging.WARNING, "TEST WARNING MSG"),
        (logging.ERROR, "TEST ERROR MSG")
    )

    def setUp(self) -> None:
        log_utils.init(should_log=False)

    def tearDown(self) -> None:
        log_utils.deinit(should_log=False)

    @classmethod
    def setUpClass(cls) -> None:
        pass

    @classmethod
    def tearDownClass(cls) -> None:
        pass

    def test_logging_basic(self) -> None:
        booplibot_logger = logging.getLogger("BoopliBot")
        test_exc = Exception("This is a test exc")

        case_msg = "Case: log records should match emitted log messages"
        with self.assertLogs(booplibot_logger, logging.DEBUG) as logs_context:
            for level, msg in self.TEST_CASES:
                with self.subTest(msg=case_msg):
                    booplibot_logger.log(level, msg, exc_info=test_exc)
                    last_record = logs_context.records[-1]

                    self.assertEqual(last_record.msg, msg)
                    self.assertEqual(last_record.levelno, level)
                    self.assertIs(last_record.exc_info[1], test_exc)

    def test_logging_queue(self) -> None:
        booplibot_logger = logging.getLogger("BoopliBot")
        # We should have only 1 handler
        self.assertEqual(len(booplibot_logger.handlers), 1)
        queue_handler = booplibot_logger.handlers[0]
        # Verify it's the handler we're expecting it to be
        self.assertIsInstance(queue_handler, logging.handlers.QueueHandler)

        case_msg = "Case: queue messages should match emitted log messages"
        with patch.object(queue_handler, "emit") as mock_emit:
            for id_, test in enumerate(self.TEST_CASES, start=1):
                with self.subTest():
                    level, msg = test
                    # Send msg
                    booplibot_logger.log(level, msg)
                    # Check the record
                    self.assertEqual(mock_emit.call_count, id_)
                    record: logging.LogRecord = mock_emit.call_args[0][0]
                    self.assertEqual(record.msg, msg)
                    self.assertEqual(record.levelno, level)

    def test_logging_listener(self) -> None:
        booplibot_logger = logging.getLogger("BoopliBot")
        listener_handlers = log_utils.log_listener.handlers

        events_map = dict()
        patches = list()
        log_counter = Counter()

        try:
            # First patch handlers so they don't actually emit
            for handler in listener_handlers:
                p = patch.object(handler, "emit")
                p.start()
                patches.append(p)

                ev = threading.Event()
                events_map[id(handler)] = ev
                def side_effect(record, ev=ev):
                    ev.set()
                handler.emit.side_effect = side_effect

            # Now emit test msgs
            for level, msg in self.TEST_CASES:
                booplibot_logger.log(level, msg)

                for handler in listener_handlers:
                    # Inc log count for all appropriate handlers
                    if level >= handler.level:
                        ev = events_map[id(handler)]
                        # 1.0 second should be enough for the thread to run the handler
                        ev.wait(timeout=1.0)
                        log_counter[id(handler)] += 1
                        ev.clear()

            # Run sub tests
            msg = "Case: log count should be equal to mock call count"
            for handler in listener_handlers:
                log_count = log_counter[id(handler)]
                call_count = handler.emit.call_count
                with self.subTest(msg=msg, level=handler.level, log_count=log_count, call_count=call_count):
                    self.assertEqual(log_count, call_count)

        except Exception as e:
            raise

        finally:
            # Always remove patches at the end
            for p in patches:
                p.stop()
