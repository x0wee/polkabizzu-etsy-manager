# Architecture

## Overview

Polkabizzu Etsy Manager is a command-line tool running locally on the shop owner's machine. It has no server, no database, and no external users — it accesses only the Polkabizzu Etsy shop.

## Components

### Phase 1 — CSV-based (current, working)

```
eRank export        BaseLinker export
     │                     │
     ▼                     ▼
 etsy_tags.csv    etsy_seo_titles_descriptions.csv
         │                 │
         └────────┬────────┘
                  ▼
         fix_etsy_seo.py
         (SEO optimizer)
                  │
                  ▼
         *_FIXED.csv files
                  │
                  ▼
         Manual import to BaseLinker → Etsy
```

**Limitation:** requires manual export → run script → manual import cycle.

---

### Phase 2 — Direct API integration (in development)

```
Local machine
┌─────────────────────────────────────────────────┐
│                                                 │
│  auth.py                                        │
│  ├─ OAuth 2.0 PKCE flow                         │
│  ├─ One-time browser consent                    │
│  └─ Token stored in .etsy_token.json            │
│                                                 │
│  client.py                                      │
│  ├─ Injects Bearer token on every request       │
│  ├─ Respects Etsy rate limits (10 req/s)        │
│  └─ Raises on 4xx/5xx with context              │
│                                                 │
│  listings.py                                    │
│  ├─ iter_active_listings()  →  GET /listings    │
│  ├─ update_listing()        →  PATCH /listing   │
│  ├─ audit_listings()        →  full report      │
│  └─ dry_run=True by default (safe)              │
│                                                 │
│  fix_etsy_seo.py (existing)                     │
│  └─ Computes optimized title + tags             │
│                                                 │
└─────────────────────────────────────────────────┘
          │                        │
          │  GET (listings_r)      │  PATCH (listings_w)
          ▼                        ▼
   ┌─────────────────────────────────┐
   │      Etsy Open API v3           │
   │  openapi.etsy.com/v3            │
   └─────────────────────────────────┘
          │
          ▼
   Polkabizzu Etsy shop
   (single shop, personal use only)
```

## Security Model

- **No server exposed to the internet.** The tool runs locally only.
- **OAuth 2.0 PKCE** — no client secret ever transmitted; code_verifier stays local.
- **Localhost callback** (`http://localhost:8080/callback`) — callback handled by a temporary HTTP server that exits immediately after receiving the code.
- **Token stored in `.etsy_token.json`** — gitignored, never committed.
- **Scopes limited to minimum required:** `listings_r listings_w` only.
- **Dry-run default:** `update_listing()` defaults to `dry_run=True` — no accidental writes.

## Data Flow

```
Etsy API → listings.py → fix_etsy_seo.py → [review] → listings.py → Etsy API
                                                ↑
                                         human approval
                                         before --apply
```

The human always sees a diff before any data is written to Etsy.

## Files NOT committed to git

```
.env                  ← API key, shop ID
.etsy_token.json      ← OAuth access token
*.csv                 ← product catalog data
venv/                 ← virtualenv
__pycache__/
```
