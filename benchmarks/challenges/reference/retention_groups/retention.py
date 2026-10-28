def removable(records, now, ttl, minimum):
    projects = {}
    for item in records:
        projects.setdefault(item['project'], []).append(item)
    protected = set()
    for group in projects.values():
        newest = sorted(group, key=lambda item: (-item['created'], item['id']))[:minimum]
        protected.update(item['id'] for item in newest)
    return sorted(item['id'] for item in records if item['id'] not in protected
                  and not item.get('pinned', False) and item['created'] < now - ttl)
