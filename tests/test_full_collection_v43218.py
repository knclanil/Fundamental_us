import os
import tempfile
import unittest
from unittest.mock import patch
from fundamentals.automated_universe import collection_plan, set_action_outputs


class FullCollectionTests(unittest.TestCase):
    def test_batch_boundaries(self):
        self.assertEqual(collection_plan(60, 2939, 100), (60, 160))
        self.assertEqual(collection_plan(2900, 2939, 100), (2900, 2939))
        self.assertEqual(collection_plan(2939, 2939, 100), (2939, 2939))

    def test_invalid_checkpoint(self):
        for args in [(-1, 100, 10), (101, 100, 10), (0, 100, 0)]:
            with self.assertRaises(ValueError):
                collection_plan(*args)

    def test_action_outputs(self):
        with tempfile.NamedTemporaryFile(mode='r+', encoding='utf-8') as f:
            with patch.dict(os.environ, {'GITHUB_OUTPUT': f.name}):
                set_action_outputs(True, 160, 2939)
            f.seek(0)
            self.assertEqual(f.read(), 'continuation=true\nnext_offset=160\ntotal=2939\n')

if __name__ == '__main__':
    unittest.main()
