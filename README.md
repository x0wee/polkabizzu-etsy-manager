# Polkabizzu Etsy Manager

> **Personal seller tool** for managing [Polkabizzu](https://www.polkabizzu.pl) Etsy shop listings — handmade polymer clay earrings, made in Poland.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Etsy API v3](https://img.shields.io/badge/Etsy%20API-v3-orange.svg)](https://developers.etsy.com/documentation/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## What is this?

Polkabizzu is a solo-run handmade jewelry shop on Etsy. As the shop grew to 60+ active listings, managing titles, tags, descriptions and categories one-by-one through the Etsy dashboard became unsustainable. This tool was built to automate that work.

**The tool is strictly personal use** — it only ever accesses the Polkabizzu shop. No multi-tenant architecture, no public API, no external users.

---

## Current Features (working today)

These are scripts currently in production use:

### SEO Optimizer (`src/seo/fix_etsy_seo.py`)
- Analyzes listing titles and ensures the primary keyword (`Polymer Clay Earrings`) appears first
- Removes duplicate words from titles (Etsy penalizes these)
- Enforces 140-character title limit with smart truncation
- Rewrites description intros to put keywords in the first 160 characters
- Replaces single-word tags with SEO-effective multi-word phrases
- Enforces Etsy's 13-tag / 20-char-per-tag constraints
- Generates a Markdown diff report of all changes

### Bulk CSV Processor (`src/seo/generate_seo_csv.py`)
- Reads product catalog exported from BaseLinker
- Applies new names and SEO tag blocks in bulk
- Outputs a re-importable CSV for BaseLinker → Etsy sync

**Example output:**

| SKU | Before | After |
|-----|--------|-------|
| PB-KOK-001 | `Kokardki Różowe - Handmade Earrings, Polymer Clay` | `Polymer Clay Bow Earrings, Pink Gold, Handmade Gift` |
| PB-KWI-003 | `Daisy Flower Earrings Clay` | `Polymer Clay Daisy Flower Earrings, 3D Floral, Gift for Her` |

---

## Planned Features (requires Etsy API key)

The next phase integrates directly with **Etsy Open API v3** to eliminate the CSV export/import cycle entirely:

| Feature | Etsy API endpoint | Scope |
|---|---|---|
| Read all shop listings | `GET /v3/application/shops/{shop_id}/listings` | `listings_r` |
| Bulk update listing title + tags | `PATCH /v3/application/shops/{shop_id}/listings/{listing_id}` | `listings_w` |
| Audit listing categories | `GET /v3/application/listings/{listing_id}` | `listings_r` |
| Validate tag lengths in real-time | (client-side validation) | — |
| Generate change preview before push | (local diff) | — |

### Planned workflow

```
┌─────────────────────────────────────────────────────────┐
│                     CLI / local script                  │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────▼───────────┐
         │   OAuth 2.0 + PKCE    │  ← one-time browser auth
         │   (auth.py)           │
         └───────────┬───────────┘
                     │  access_token (stored locally)
         ┌───────────▼───────────┐
         │   EtsyClient          │  ← rate-limited HTTP client
         │   (client.py)         │
         └───────────┬───────────┘
                     │
         ┌───────────▼───────────┐
         │   ListingManager      │  ← CRUD for listings
         │   (listings.py)       │
         └───────────┬───────────┘
                     │
         ┌───────────▼───────────┐
         │   SEO Engine          │  ← existing optimizer
         │   (fix_etsy_seo.py)   │
         └─────────────────────--┘
```

---

## Tech Stack

- **Python 3.11+** — no framework, plain scripts + stdlib
- **requests** — HTTP client for Etsy API v3
- **python-dotenv** — local credentials management
- **OAuth 2.0 with PKCE** — Etsy's required auth flow
- **CSV / standard output** — no database, keeps it simple

---

## Installation

```bash
git clone https://github.com/YOUR_USERNAME/polkabizzu-etsy-manager
cd polkabizzu-etsy-manager
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Fill in your credentials in .env
```

---

## Configuration

See `.env.example` for all required variables. The tool reads credentials from `.env` — never hardcoded, never committed.

Required Etsy API scopes: `listings_r listings_w`

---

## Usage

### Run the SEO optimizer on a CSV export

```bash
# Place your BaseLinker export as etsy_seo_titles_descriptions.csv
# and etsy_tags.csv in the working directory, then:
python src/seo/fix_etsy_seo.py
```

Outputs: `*_FIXED.csv` files + `etsy_seo_fix_report.md`

### (Planned) Authenticate with Etsy

```bash
python src/api/auth.py
# Opens browser for OAuth consent → saves token locally
```

### (Planned) Sync SEO changes directly to Etsy

```bash
python src/api/listings.py --dry-run   # preview changes
python src/api/listings.py --apply     # push to Etsy API
```

---

## Project Status

| Module | Status |
|---|---|
| SEO title optimizer | ✅ Production use |
| CSV bulk processor | ✅ Production use |
| Etsy OAuth 2.0 client | 🔧 In development |
| Listing read/update API | 🔧 In development |
| Change preview / dry-run | 📋 Planned |

**Waiting on Etsy API key approval** to complete the direct integration.

---

## About the Shop

[Polkabizzu](https://www.polkabizzu.pl) is a small handmade jewelry brand from Poland. We make polymer clay earrings — lightweight, colorful, and hypoallergenic. All pieces are handcrafted by one person.

- 🛍️ Etsy shop: [polkabizzu.etsy.com](https://www.etsy.com/shop/polkabizzu)
- 🌐 Website: [polkabizzu.pl](https://www.polkabizzu.pl)

---

## Author

**Jakub Janocha** — IT Manager & developer running the Polkabizzu brand with his partner Natalia.

- 12+ years professional software development experience
- Building internal tools for the shop since 2024
- Contact: biuro@polkabizzu.pl

---

## License

MIT — personal use. Not intended for redistribution as a product.
