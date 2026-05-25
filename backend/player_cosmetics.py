import time
from typing import Any, Dict, Optional

from shop_catalog import EMBLEM_LABELS, SPONSOR_TITLE


def _row_get(row: Any, key: str, default=None):
    try:
        return row[key]
    except (KeyError, IndexError, TypeError):
        return default


def _empty_cosmetics() -> Dict[str, Any]:
    return {
        "is_sponsor": False,
        "sponsor_title": None,
        "monthly_expires_at": None,
        "shop_emblem": None,
        "shop_emblem_label": None,
        "has_plaque": False,
        "showcase_tagline": None,
    }


def cosmetics_from_row(row: Any, now: Optional[int] = None) -> Dict[str, Any]:
    if int(_row_get(row, "is_system_player", 0) or 0):
        return _empty_cosmetics()
    now = now if now is not None else int(time.time())
    monthly_expires_at = _row_get(row, "monthly_expires_at")
    shop_emblem = _row_get(row, "shop_emblem")
    showcase_tagline = _row_get(row, "showcase_tagline")
    is_sponsor = bool(monthly_expires_at and int(monthly_expires_at) > now)
    has_plaque = bool(shop_emblem)
    return {
        "is_sponsor": is_sponsor,
        "sponsor_title": SPONSOR_TITLE if is_sponsor else None,
        "monthly_expires_at": int(monthly_expires_at) if monthly_expires_at else None,
        "shop_emblem": shop_emblem,
        "shop_emblem_label": EMBLEM_LABELS.get(shop_emblem) if shop_emblem else None,
        "has_plaque": has_plaque,
        "showcase_tagline": showcase_tagline or None,
    }


def merge_cosmetics_into_player(player: Dict[str, Any], row: Any, now: Optional[int] = None) -> Dict[str, Any]:
    merged = dict(player)
    merged.update(cosmetics_from_row(row, now))
    return merged


def attach_cosmetics(entry: Dict[str, Any], row: Any, now: Optional[int] = None) -> Dict[str, Any]:
    payload = cosmetics_from_row(row, now)
    entry["is_sponsor"] = payload["is_sponsor"]
    entry["sponsor_title"] = payload["sponsor_title"]
    entry["shop_emblem"] = payload["shop_emblem"]
    entry["shop_emblem_label"] = payload["shop_emblem_label"]
    entry["showcase_tagline"] = payload["showcase_tagline"]
    return entry
