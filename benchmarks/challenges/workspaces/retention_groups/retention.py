def removable(records, now, ttl, minimum):
    newest = sorted(records, key=lambda item: item['created'], reverse=True)[:minimum]
    protected = {item['id'] for item in newest}
    return [item['id'] for item in records if item['id'] not in protected and item['created'] <= now - ttl]
