def recipient_addresses(users):
    return sorted({user['email'] for user in users if user.get('enabled')})
