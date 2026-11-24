"""v4.1.3: loss-preserving migration of legacy duplicate financial periods."""
from datetime import datetime, timezone
from pymongo import ASCENDING

KEY = [('cik', ASCENDING), ('period_end', ASCENDING)]


def score(doc):
    return (len(doc.get('metrics') or {}), len(doc.get('metric_sources') or {}),
            str(doc.get('updated_at') or ''), str(doc['_id']))


def migrate_collection(db, name, *, dry_run=False):
    """Archive duplicates BEFORE modifying records; preserve conflicting versions.

    Archive documents have deterministic IDs, so retries are idempotent. No
    destructive operation occurs unless its archive copy has been verified.
    """
    coll = db[name]
    archive = db['financial_duplicate_archive']
    groups = coll.aggregate([
        {'$group': {'_id': {'cik': '$cik', 'period_end': '$period_end'},
                    'ids': {'$push': '$_id'}, 'count': {'$sum': 1}}},
        {'$match': {'count': {'$gt': 1}}}
    ], allowDiskUse=True)
    result = {'groups': 0, 'archived': 0, 'removed': 0, 'conflicts': 0}
    for group in groups:
        docs = list(coll.find({'_id': {'$in': group['ids']}}))
        if len(docs) < 2:
            continue
        result['groups'] += 1
        docs.sort(key=score, reverse=True)
        keeper, extras = docs[0], docs[1:]
        merged = dict(keeper.get('metrics') or {})
        sources = dict(keeper.get('metric_sources') or {})
        for other in extras:
            for key, value in (other.get('metrics') or {}).items():
                if key not in merged:
                    merged[key] = value
                    if key in (other.get('metric_sources') or {}):
                        sources[key] = other['metric_sources'][key]
                elif merged[key] != value:
                    result['conflicts'] += 1
        if dry_run:
            result['archived'] += len(extras)
            continue
        for other in extras:
            archive_id = f'{name}:{other["_id"]}'
            archive.update_one({'_id': archive_id}, {'$setOnInsert': {
                'source_collection': name, 'original_id': other['_id'],
                'archived_at': datetime.now(timezone.utc), 'document': other,
                'reason': 'duplicate_cik_period_end_v4.1.3'}}, upsert=True)
            if archive.find_one({'_id': archive_id}) is None:
                raise RuntimeError('Archive verification failed; stopping migration')
            result['archived'] += 1
        coll.update_one({'_id': keeper['_id']}, {'$set': {
            'metrics': merged, 'metric_sources': sources}})
        deleted = coll.delete_many({'_id': {'$in': [d['_id'] for d in extras]}})
        if deleted.deleted_count != len(extras):
            raise RuntimeError('Unexpected concurrent changes; migration halted')
        result['removed'] += deleted.deleted_count
    if not dry_run:
        coll.create_index(KEY, unique=True, name='cik_1_period_end_1')
    return result


def migrate_all(db, *, dry_run=False):
    return {name: migrate_collection(db, name, dry_run=dry_run)
            for name in ('financial_annual', 'financial_quarterly')}
