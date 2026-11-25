"""v4.1.8.3: read-only, bounded SEC Company Facts source inventory."""
from collections import Counter
from datetime import date
from .normalize import TAGS, UNITS

def inventory(payload, today=None):
    today = today or date.today()
    facts = payload.get('facts') or {}
    namespaces = {name: len(tags) for name, tags in sorted(facts.items()) if isinstance(tags, dict)}
    gaap = facts.get('us-gaap') or {}
    recognized = {}
    all_forms = Counter()
    annual_observations = 0
    annual_recent = 0
    annual_with_duration = 0
    latest_annual_ends = set()
    total_observations = 0
    for tag, entry in gaap.items():
        units = entry.get('units') or {}
        for observations in units.values():
            if not isinstance(observations, list):
                continue
            total_observations += len(observations)
            for obs in observations:
                form = obs.get('form') or 'missing'
                all_forms[form] += 1
                if form in ('10-K', '10-K/A'):
                    annual_observations += 1
                    try:
                        end = date.fromisoformat(obs['end'])
                        filed = date.fromisoformat(obs['filed'])
                    except (ValueError, TypeError, KeyError):
                        continue
                    if end <= today and filed <= today and end.year >= today.year-6:
                        annual_recent += 1
                        latest_annual_ends.add(str(end))
                        if obs.get('start'):
                            try:
                                days = (end - date.fromisoformat(obs['start'])).days + 1
                                if 330 <= days <= 380:
                                    annual_with_duration += 1
                            except (ValueError, TypeError):
                                pass
    for metric, tags in TAGS.items():
        expected = UNITS.get(metric, 'USD')
        present = [tag for tag in tags if (gaap.get(tag) or {}).get('units', {}).get(expected)]
        recognized[metric] = present[:4]
    available = sorted(gaap)
    return {
        'cik': payload.get('cik'),
        'entity_name': str(payload.get('entityName') or '')[:100],
        'namespaces': namespaces,
        'us_gaap_tag_count': len(gaap),
        'us_gaap_observations': total_observations,
        'form_counts': dict(all_forms.most_common(10)),
        'annual_10k_observations': annual_observations,
        'recent_10k_observations': annual_recent,
        'recent_10k_annual_duration_observations': annual_with_duration,
        'recent_10k_end_dates_sample': sorted(latest_annual_ends, reverse=True)[:8],
        'recognized_metric_tags': {k: v for k, v in recognized.items() if v},
        'missing_metric_names': [k for k, v in recognized.items() if not v],
        'unrecognized_gaap_tags_sample': [t for t in available if t not in {x for group in TAGS.values() for x in group}][:15],
    }
