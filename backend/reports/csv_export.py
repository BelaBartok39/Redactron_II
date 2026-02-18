"""CSV export — one row per finding."""

from __future__ import annotations

import csv
from pathlib import Path


def generate_csv(data: dict, output_path: Path) -> None:
    """Generate a flat CSV export with one row per finding.

    Args:
        data: Report data from generator._fetch_batch_data().
        output_path: Where to write the CSV.
    """
    batch = data["batch"]
    documents = data["documents"]
    findings_by_doc = data["findings_by_doc"]

    # Build a lookup for document filename by id
    doc_lookup = {d["id"]: d["filename"] for d in documents}

    fieldnames = [
        "batch_name",
        "document_filename",
        "page_number",
        "pii_type",
        "confidence",
        "context_snippet",
        "char_offset",
        "char_length",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for doc_info in documents:
            doc_id = doc_info["id"]
            doc_findings = findings_by_doc.get(doc_id, [])

            for f in doc_findings:
                writer.writerow({
                    "batch_name": batch["name"],
                    "document_filename": doc_lookup.get(f["document_id"], "unknown"),
                    "page_number": f["page_number"],
                    "pii_type": f["pii_type"],
                    "confidence": f["confidence"],
                    "context_snippet": f["context_snippet"],
                    "char_offset": f["char_offset"],
                    "char_length": f["char_length"],
                })
