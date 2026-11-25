"""Read-only MongoDB collection and index inventory.

Usage: MONGODB_URI=... python -m scripts.db_inventory --output artifacts/db-inventory.json
No document content is exported and no database mutations are performed.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path


def collect_inventory(db):
    result = {"database": db.name, "generated_at": datetime.now(timezone.utc).isoformat(), "collections": []}
    for name in sorted(db.list_collection_names()):
        if name.startswith('system.'):
            continue
        coll = db[name]
        stats = db.command('collStats', name)
        indexes = []
        for ix in coll.list_indexes():
            indexes.append({"name": ix['name'], "keys": list(ix['key'].items()),
                            "unique": bool(ix.get('unique', False)),
                            "sparse": bool(ix.get('sparse', False)),
                            "ttl_seconds": ix.get('expireAfterSeconds')})
        result['collections'].append({"name": name, "documents": stats.get('count', 0),
            "data_bytes": stats.get('size', 0), "storage_bytes": stats.get('storageSize', 0),
            "index_bytes": stats.get('totalIndexSize', 0), "indexes": indexes})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='artifacts/db-inventory.json')
    args = parser.parse_args()
    uri = os.getenv('MONGODB_URI')
    if not uri:
        parser.error('MONGODB_URI must be set')
    from pymongo import MongoClient
    client = MongoClient(uri, serverSelectionTimeoutMS=15000)
    try:
        db = client[os.getenv('MONGODB_DATABASE', 'maketdata')]
        report = collect_inventory(db)
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2, default=str) + '\n', encoding='utf-8')
        print(f"Read-only inventory: {len(report['collections'])} collections; output={path}")
    finally:
        client.close()


if __name__ == '__main__':
    main()
