#!/usr/bin/env python3
"""
Bulk SEO CSV processor for Etsy listings.

Reads a BaseLinker product export (CSV) and applies:
- Updated listing titles (SEO-optimized)
- Appended SEO tag blocks to descriptions

Output is a re-importable CSV for BaseLinker → Etsy sync.

Usage:
    python src/seo/generate_seo_csv.py \
        --input BL_Produkty_export.csv \
        --output IMPORT_BASELINKER_SEO.csv
"""

import argparse
import csv
from pathlib import Path

# Mapping: produkt_id -> (new_title, seo_tag_html_block)
# Edit this dict to add/update listings before running.
LISTING_UPDATES: dict[str, tuple[str, str]] = {
    # Example entries (real data kept private):
    # "487406738": (
    #     "Polymer Clay Pearl Petal Earrings - Handmade Gift",
    #     '<p><b>Tags:</b> polymer clay earrings, handmade jewelry, gift for her</p>',
    # ),
}


def process(input_file: Path, output_file: Path) -> int:
    """Apply updates and write the output CSV. Returns count of updated rows."""
    rows = []

    with open(input_file, encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=";", quotechar='"')
        header = next(reader)

        for row in reader:
            if len(row) < 10:
                continue
            produkt_id = row[0]
            stara_nazwa = row[1]
            sku = row[4]
            opis = row[9]

            if produkt_id in LISTING_UPDATES:
                nowa_nazwa, blok_seo = LISTING_UPDATES[produkt_id]
                rows.append({
                    "produkt_id": produkt_id,
                    "sku": sku,
                    "stara_nazwa": stara_nazwa,
                    "nowa_nazwa": nowa_nazwa,
                    "opis": opis + blok_seo,
                })

    with open(output_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter=";", quotechar='"', quoting=csv.QUOTE_ALL)
        writer.writerow(["produkt_id", "sku", "stara_nazwa", "nowa_nazwa", "opis"])
        for row in rows:
            writer.writerow([
                row["produkt_id"], row["sku"],
                row["stara_nazwa"], row["nowa_nazwa"], row["opis"],
            ])

    return len(rows)


def main():
    parser = argparse.ArgumentParser(description="Bulk SEO CSV processor")
    parser.add_argument("--input", type=Path, required=True, help="BaseLinker export CSV")
    parser.add_argument("--output", type=Path, required=True, help="Output CSV path")
    args = parser.parse_args()

    count = process(args.input, args.output)
    print(f"Saved {count} updated rows to {args.output}")


if __name__ == "__main__":
    main()
