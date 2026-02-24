#!/usr/bin/env python3
"""
Listing read/update operations for Polkabizzu Etsy shop.

Provides:
- Fetch all active listings from the shop
- Read individual listing details (title, tags, description, category)
- Apply SEO-optimized title and tags in bulk
- Dry-run mode: preview changes without pushing to API

Etsy API docs:
  GET  /v3/application/shops/{shop_id}/listings
  GET  /v3/application/listings/{listing_id}
  PATCH /v3/application/shops/{shop_id}/listings/{listing_id}
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

from dotenv import load_dotenv

from .client import EtsyClient

load_dotenv()

SHOP_ID = os.getenv("ETSY_SHOP_ID")
PAGE_SIZE = 100  # Etsy max per page


@dataclass
class Listing:
    listing_id: int
    title: str
    description: str
    tags: list[str]
    state: str
    url: str
    raw: dict = field(default_factory=dict, repr=False)


class ListingManager:
    """High-level interface for managing Etsy listings."""

    def __init__(self, client: EtsyClient | None = None):
        self.client = client or EtsyClient()

    def iter_active_listings(self) -> Iterator[Listing]:
        """Yield all active listings from the shop, page by page."""
        offset = 0
        while True:
            data = self.client.get(
                f"/application/shops/{SHOP_ID}/listings",
                params={
                    "state": "active",
                    "limit": PAGE_SIZE,
                    "offset": offset,
                    "includes": ["Images"],
                },
            )
            results = data.get("results", [])
            for raw in results:
                yield Listing(
                    listing_id=raw["listing_id"],
                    title=raw["title"],
                    description=raw["description"],
                    tags=raw.get("tags", []),
                    state=raw["state"],
                    url=raw.get("url", ""),
                    raw=raw,
                )
            count = data.get("count", 0)
            offset += PAGE_SIZE
            if offset >= count:
                break

    def get_listing(self, listing_id: int) -> Listing:
        """Fetch a single listing by ID."""
        raw = self.client.get(f"/application/listings/{listing_id}")
        return Listing(
            listing_id=raw["listing_id"],
            title=raw["title"],
            description=raw["description"],
            tags=raw.get("tags", []),
            state=raw["state"],
            url=raw.get("url", ""),
            raw=raw,
        )

    def update_listing(
        self,
        listing_id: int,
        title: str | None = None,
        tags: list[str] | None = None,
        description: str | None = None,
        dry_run: bool = True,
    ) -> dict:
        """
        Update a listing's title, tags and/or description.

        Args:
            listing_id: Etsy listing ID
            title: New title (max 140 chars)
            tags: New tag list (max 13 tags, each max 20 chars)
            description: New description
            dry_run: If True, print the change but do NOT call the API

        Returns:
            The API response (or simulated response in dry_run mode)
        """
        payload = {}
        if title is not None:
            assert len(title) <= 140, f"Title too long: {len(title)} chars"
            payload["title"] = title
        if tags is not None:
            assert len(tags) <= 13, f"Too many tags: {len(tags)}"
            for t in tags:
                assert len(t) <= 20, f"Tag too long: '{t}' ({len(t)} chars)"
            payload["tags"] = tags
        if description is not None:
            payload["description"] = description

        if not payload:
            return {}

        if dry_run:
            print(f"[DRY RUN] Would PATCH listing {listing_id}:")
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            return {"dry_run": True, "listing_id": listing_id, "payload": payload}

        return self.client.patch(
            f"/application/shops/{SHOP_ID}/listings/{listing_id}",
            data=payload,
        )

    def audit_listings(self, output_file: Path | None = None) -> list[dict]:
        """
        Fetch all active listings and return a summary for review.
        Useful for identifying listings with suboptimal titles/tags.
        """
        results = []
        print("Fetching all active listings...")

        for listing in self.iter_active_listings():
            issues = []
            if not listing.title.lower().startswith("polymer clay"):
                issues.append("title: missing 'Polymer Clay' prefix")
            if len(listing.tags) < 10:
                issues.append(f"tags: only {len(listing.tags)} tags (aim for 13)")
            single_word_tags = [t for t in listing.tags if " " not in t]
            if single_word_tags:
                issues.append(f"tags: single-word tags: {single_word_tags}")

            results.append({
                "listing_id": listing.listing_id,
                "title": listing.title,
                "tag_count": len(listing.tags),
                "issues": issues,
                "url": listing.url,
            })

        if output_file:
            output_file.write_text(
                json.dumps(results, indent=2, ensure_ascii=False)
            )
            print(f"Audit saved to {output_file}")

        print(f"Total: {len(results)} listings, "
              f"{sum(1 for r in results if r['issues'])} with issues")
        return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Polkabizzu Etsy Listing Manager")
    parser.add_argument("--audit", action="store_true", help="Audit all listings")
    parser.add_argument("--audit-output", type=Path, default=Path("audit.json"))
    args = parser.parse_args()

    manager = ListingManager()

    if args.audit:
        manager.audit_listings(output_file=args.audit_output)
