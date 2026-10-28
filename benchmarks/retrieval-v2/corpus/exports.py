import csv
import io


def export_csv(rows, columns):
    """CSV serialization quotes delimiters and writes a stable column order."""
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=columns, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def redact_export(rows, private_columns):
    """Remove private fields before serializing exported records."""
    return [{key: value for key, value in row.items() if key not in private_columns} for row in rows]
