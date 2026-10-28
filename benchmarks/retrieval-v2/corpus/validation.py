def required_fields(record, fields):
    return all(field in record for field in fields)
