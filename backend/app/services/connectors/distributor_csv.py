"""Parse DistroKid / TuneCore / generic distributor CSV exports into draft claims."""

from __future__ import annotations

import csv
import io
from typing import Any


def _norm(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum())


_ISRC = frozenset({"isrc", "isrc-code", "isrc_code"})
_ISWC = frozenset({"iswc", "iswc-code", "iswc_code"})
_UPC = frozenset({"upc", "ean", "barcode"})
_WRITER = frozenset({"writer", "songwriter", "composer", "author"})
_SHARE = frozenset({"share", "split", "percentage", "ownership"})
_ROLE = frozenset({"role", "credit", "creditrole"})
_NAME = frozenset({"name", "fullname", "contributor", "artist"})
_RIGHT = frozenset({"right", "righttype", "right_type"})


def parse_distributor_csv(content: bytes | str) -> list[dict[str, Any]]:
    text = content.decode("utf-8-sig") if isinstance(content, bytes) else content
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return []
    fields = {_norm(f): f for f in reader.fieldnames if f}
    drafts: list[dict[str, Any]] = []
    for index, row in enumerate(reader):
        ref = {"row": index, "source": "distributor_export"}
        isrc_key = next((fields[k] for k in _ISRC if k in fields), None)
        iswc_key = next((fields[k] for k in _ISWC if k in fields), None)
        upc_key = next((fields[k] for k in _UPC if k in fields), None)
        identifiers: dict[str, Any] = {}
        if isrc_key and (row.get(isrc_key) or "").strip():
            identifiers["isrc"] = row[isrc_key].strip()
        if iswc_key and (row.get(iswc_key) or "").strip():
            identifiers["iswc"] = row[iswc_key].strip()
        if upc_key and (row.get(upc_key) or "").strip():
            identifiers["upc"] = row[upc_key].strip()
        if identifiers:
            drafts.append({"claim_type": "identifiers", "value": identifiers, "source_ref": ref})

        name_key = next((fields[k] for k in _NAME | _WRITER if k in fields), None)
        role_key = next((fields[k] for k in _ROLE if k in fields), None)
        share_key = next((fields[k] for k in _SHARE if k in fields), None)
        right_key = next((fields[k] for k in _RIGHT if k in fields), None)
        name = (row.get(name_key) or "").strip() if name_key else ""
        role = (row.get(role_key) or "writer").strip().lower() if role_key else "writer"
        if name:
            drafts.append(
                {
                    "claim_type": "credit",
                    "value": {"role": role or "writer", "name": name},
                    "source_ref": ref,
                }
            )
        if name and share_key and (row.get(share_key) or "").strip():
            raw_share = row[share_key].replace("%", "").strip()
            try:
                pct = float(raw_share)
            except ValueError:
                continue
            right_type = "composition"
            if right_key and "master" in (row.get(right_key) or "").lower():
                right_type = "master"
            drafts.append(
                {
                    "claim_type": "split",
                    "value": {"payee_name_or_id": name, "percentage": pct, "right_type": right_type},
                    "source_ref": ref,
                }
            )
    return drafts
