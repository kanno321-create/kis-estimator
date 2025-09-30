KIS Estimation FullSpec Pack
UTC: 20250930_183858Z

This pack follows the project's preferred layout.

Included (as available from provided archives):
- KIS/Knowledge/packs/         # Estimation rules/logic (JSON/YAML)
- KIS/Knowledge/guides/        # Guides (Spec_KIT, Pricing_Rules, Sizing_Rules)
- data/catalog/                # Product master (breakers/enclosures) + size tables(under data/catalog/size/)
- data/pricebook/              # Unified pricebook (generated) and any pricebook/uom files
- db/seed/                     # seed_*.sql
- migrations/                  # SQL migrations (if present)
- docs/                        # Operations.md, Parsing_Rules.md (as alternates)
- out/                         # Evidence snapshots (EVIDENCE/PARSER/SSE/SSOT) if present

Notes:
- Only files present in the uploaded archives are included.
- Generated pricebook is placed at data/pricebook/pricebook.csv if available.
