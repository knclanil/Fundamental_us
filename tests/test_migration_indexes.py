"""Regression tests for v4.1.3 E11000 legacy-index collision."""
import unittest
from unittest.mock import MagicMock
from fundamentals.migrate import migrate_collection

class MigrationIndexTests(unittest.TestCase):
    def test_old_period_unique_index_removed_after_new_created(self):
        db = MagicMock()
        coll = db.__getitem__.return_value
        coll.list_indexes.side_effect = [
            [{ 'name':'_id_', 'key':{'_id':1}, 'unique':True},
             { 'name':'cik_1_period_1','key':{'cik':1,'period':1},'unique':True}],
            [{ 'name':'_id_', 'key':{'_id':1}, 'unique':True},
             { 'name':'cik_1_period_end_1','key':{'cik':1,'period_end':1},'unique':True}]
        ]
        coll.aggregate.return_value = []
        result = migrate_collection(db,'financial_annual')
        coll.create_index.assert_called_once_with([('cik',1),('period_end',1)],unique=True,name='cik_1_period_end_1')
        coll.drop_index.assert_called_once_with('cik_1_period_1')
        self.assertEqual(result['obsolete_indexes_dropped'],1)

    def test_never_drop_legacy_if_new_index_fails(self):
        db = MagicMock(); coll = db.__getitem__.return_value
        coll.list_indexes.return_value = [{'name':'cik_1_period_1','key':{'cik':1,'period':1},'unique':True}]
        coll.aggregate.return_value = []
        coll.create_index.side_effect = RuntimeError('duplicate period end')
        with self.assertRaises(RuntimeError): migrate_collection(db,'financial_quarterly')
        coll.drop_index.assert_not_called()

if __name__=='__main__': unittest.main()
