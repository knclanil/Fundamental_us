"""Idempotent SEC Company Facts ingestion into MongoDB."""
import argparse
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from pymongo import MongoClient, ASCENDING
from pymongo.errors import DocumentTooLarge
from .sec_client import SecClient

def utcnow():
    return datetime.now(timezone.utc)

def ensure_indexes(db):
    db.companies.create_index([("ticker", ASCENDING)])
    db.collection_state.create_index([("next_retry_at", ASCENDING)])
    db.company_facts_raw.create_index([("fetched_at", ASCENDING)])

def as_utc(value):
    """PyMongo returns naive UTC datetimes by default; normalize before comparisons."""
    if value is None:
        return None
    if not isinstance(value, datetime):
        raise TypeError(f"Expected datetime, received {type(value).__name__}")
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def due(state, now, refresh_days):
    now = as_utc(now)
    if not state:
        return True
    retry_at = as_utc(state.get("next_retry_at"))
    if retry_at and retry_at > now:
        return False
    last_success = as_utc(state.get("last_success_at"))
    return not last_success or last_success <= now - timedelta(days=refresh_days)

def run(db, sec, limit=10, refresh_days=7):
    if limit < 1 or refresh_days < 0:
        raise ValueError("limit must be positive and refresh-days nonnegative")
    ensure_indexes(db)
    run_id = str(uuid4())
    started = utcnow()
    db.pipeline_runs.insert_one({"_id": run_id, "started_at": started, "status": "running"})
    counts = {"selected": 0, "success": 0, "skipped": 0, "failed": 0}
    try:
        rows = sec.tickers()
        # Limit is number of distinct SEC-listed companies examined, not number of successes.
        for row in rows[:limit]:
            cik = int(row["cik_str"])
            now = utcnow()
            db.companies.update_one({"_id": cik}, {"$set": {"ticker": row["ticker"], "name": row["title"], "updated_at": now}}, upsert=True)
            state = db.collection_state.find_one({"_id": cik})
            if not due(state, now, refresh_days):
                counts["skipped"] += 1
                continue
            counts["selected"] += 1
            try:
                facts = sec.company_facts(cik)
                if not isinstance(facts, dict) or "facts" not in facts or int(facts.get("cik", -1)) != cik:
                    raise ValueError(f"Invalid SEC Company Facts payload for CIK {cik}")
                # Preserve raw filing dates, fiscal periods, accession numbers and units.
                db.company_facts_raw.replace_one({"_id": cik}, {"_id": cik, "fetched_at": utcnow(), "payload": facts}, upsert=True)
                db.collection_state.update_one({"_id": cik}, {"$set": {"last_success_at": utcnow(), "last_error": None, "next_retry_at": None, "failures": 0}}, upsert=True)
                counts["success"] += 1
            except Exception as exc:
                failures = int((state or {}).get("failures", 0)) + 1
                delay_hours = min(2 ** min(failures, 6), 48)
                db.collection_state.update_one({"_id": cik}, {"$set": {"last_error": f"{type(exc).__name__}: {exc}"[:500], "failures": failures, "next_retry_at": utcnow() + timedelta(hours=delay_hours)}}, upsert=True)
                counts["failed"] += 1
                print(f"CIK {cik}: {type(exc).__name__}: {exc}", flush=True)
        status = "completed" if counts["failed"] == 0 else "completed_with_errors"
    except Exception as exc:
        status = "failed"
        db.pipeline_runs.update_one({"_id": run_id}, {"$set": {"finished_at": utcnow(), "status": status, "counts": counts, "error": str(exc)[:500]}})
        raise
    db.pipeline_runs.update_one({"_id": run_id}, {"$set": {"finished_at": utcnow(), "status": status, "counts": counts}})
    return counts

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--refresh-days", type=int, default=7)
    args = parser.parse_args()
    uri = os.environ.get("MONGODB_URI")
    if not uri:
        parser.error("MONGODB_URI environment variable is required")
    sec = SecClient(os.environ.get("SEC_USER_AGENT"))
    client = MongoClient(uri, tz_aware=True, serverSelectionTimeoutMS=15000)
    try:
        client.admin.command("ping")
        db = client[os.environ.get("MONGODB_DATABASE", "maketdata")]
        counts = run(db, sec, args.limit, args.refresh_days)
        print(counts)
        if counts["failed"]:
            raise SystemExit(1)
    finally:
        client.close()

if __name__ == "__main__":
    main()
