# Internal tools

Partnership K-1 PDF filling and tax-specific generators that contain **entity-specific fields** are kept out of the public tree by default.

- Use a **private workspace** (or encrypted storage) for filled IRS PDFs, SSNs, and EIN-specific field maps.
- Generic automation patterns live under `backend/partnership_tools/` only if you add them later with **no** hardcoded identifiers.

