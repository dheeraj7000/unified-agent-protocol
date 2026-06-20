import unittest

from uap.context import ContextManager
from uap.models import ContextRequest


class ContextManagerTest(unittest.TestCase):
    def test_field_mask_and_item_limit(self):
        manager = ContextManager()
        result = [
            {"a": 1, "b": 2},
            {"a": 3, "b": 4},
            {"a": 5, "b": 6},
        ]
        compact = manager.compact(result, ContextRequest(fields=["a"], max_items=2), 1000)
        self.assertEqual(compact[0], {"a": 1})
        self.assertEqual(compact[1], {"a": 3})
        self.assertTrue(compact[2]["_truncated"])


if __name__ == "__main__":
    unittest.main()
