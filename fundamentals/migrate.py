"""v4.1.4: non-destructive, fail-closed index migration.

Never merge records with different period_end values. Legacy period indexes are
removed only after their definitions are inspected and the replacement exists.
"""
from datetime import datetime, timezone
from pymongo import ASCENDING

KEY = [('cik', ASCENDING), ('period_end', ASCENDING)]
LEGACY = [('cik', ASCENDING), ('period', ASCENDING)]


def score(doc):
    return (len(doc.get('metrics') or {}), len(doc.get('metric_sources') or {}),
            str(doc.get('updated_at') or ''), str(doc['_id']))

def _key(index):
    return list(index['key'].items())


def _duplicates(coll):
    return list(coll.aggregate([
        {'$group': {'_id': {'cik': '$cik', 'period_end': '$period_end'}, 'ids': {'$push': '$_id'}, 'n': {'$sum': 1}}},
        {'$match': {'n': {'$gt': 1}}}
    ], allowDiskUse=True))


def migrate_collection(db, name, *, dry_run=False):
    coll = db[name]
    archive = db['financial_duplicate_archive']
    result = {'groups': 0, 'archived': 0, 'removed': 0, 'conflicts': 0, 'obsolete_indexes_dropped': 0}
    indexes = list(coll.list_indexes())
    # Do not remove unknown unique indexes: they might encode intentional business rules.
    old = [i for i in indexes if i.get('unique') and _key(i) == LEGACY]
    replacement = [i for i in indexes if _key(i) == KEY]
    if replacement and not all(i.get('unique') for i in replacement):
        raise RuntimeError(f'{name}: period-end index exists but is not unique; manual review required')
    for group in _duplicates(coll):
        docs = list(coll.find({'_id': {'$in': group['ids']}}))
        if len(docs) < 2:
            continue
        # Distinct fiscal periods sharing an end date cannot be safely merged.
        identities = {(d.get('period_type'), d.get('fiscal_year'), d.get('fiscal_period')) for d in docs if d.get('fiscal_year') is not None}
        if len(identities) > 1:
            raise RuntimeError(f'{name}: ambiguous fiscal identities for {group["_id"]}; no records deleted')
        result['groups'] += 1
        docs.sort(key=score, reverse=True)
        keeper, extras = docs[0], docs[1:]
        merged = dict(keeper.get('metrics') or {})
        sources = dict(keeper.get('metric_sources') or {})
        for other in extras:
            for metric, value in (other.get('metrics') or {}).items():
                if metric not in merged:
                    merged[metric] = value
                    if metric in (other.get('metric_sources') or {}):
                        sources[metric] = other['metric_sources'][metric]
                elif merged[metric] != value:
                    result['conflicts'] += 1
        if dry_run:
            result['archived'] += len(extras)
            continue
        # Archive *all* versions including the keeper, before any mutation.
        for doc in docs:
            aid = f'{name}:{doc["_id"]}'
            archive.update_one({'_id': aid}, {'$setOnInsert': {
                'source_collection': name, 'original_id': doc['_id'],
                'archived_at': datetime.now(timezone.utc), 'document': doc,
                'reason': 'v4.1.4_period_end_reconciliation'}}, upsert=True)
            if archive.find_one({'_id': aid}) is None:
                raise RuntimeError('Archive verification failed')
            result['archived'] += 1
        coll.update_one({'_id': keeper['_id']}, {'$set': {'metrics': merged, 'metric_sources': sources}})
        for other in extras:
            deleted = coll.delete_one({'_id': other['_id']})
            if deleted.deleted_count != 1:
                raise RuntimeError('Concurrent migration detected; stopped')
            result['removed'] += 1
    if not dry_run:
        # First establish new invariant. If this fails, old indexes remain intact.
        coll.create_index(KEY, unique=True, name='cik_1_period_end_1')
        for idx in old:
            coll.drop_index(idx['name'])
            result['obsolete_indexes_dropped'] += 1
        # Fail closed on unexpected unique constraints on period fields.
        for idx in coll.list_indexes():
            if idx.get('unique') and idx['name'] != '_id_' and _key(idx) != KEY:
                if any(field in ('period', 'period_end', 'cik') for field, _ in _key(idx)):
                    raise RuntimeError(f'{name}: unexpected unique index {idx["name"]}; inspect before collection')
    return result


def migrate_all(db, *, dry_run=False):
    return {name: migrate_collection(db, name, dry_run=dry_run)
            for name in ('financial_annual', 'financial_quarterly')}
