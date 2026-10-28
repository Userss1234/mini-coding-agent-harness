def retained_by_project(records, minimum):
    """Keep newest artifact records independently for each project."""
    grouped = {}
    for item in records:
        grouped.setdefault(item['project'], []).append(item)
    return {item['id'] for group in grouped.values()
            for item in sorted(group, key=lambda row: -row['created'])[:minimum]}


def expired_artifacts(records, cutoff, protected):
    """Pinned artifacts never expire; strict cutoff leaves equal timestamps intact."""
    return sorted(item['id'] for item in records if item['created'] < cutoff
                  and not item.get('pinned') and item['id'] not in protected)
