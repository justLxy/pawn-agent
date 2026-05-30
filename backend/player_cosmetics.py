import time
from typing import Any, Dict, Optional

from shop_catalog import (
    CHAT_ACCENT_LABELS,
    DEFAULT_CHAT_ACCENT,
    DEFAULT_PLAQUE_TITLE,
    DEFAULT_SHOWCASE_MOOD,
    DEFAULT_SIGN_STYLE,
    EMBLEM_LABELS,
    PLAQUE_TITLE_LABELS,
    SHOWCASE_MOOD_LABELS,
    SIGN_STYLE_LABELS,
    SPONSOR_TITLE,
)


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
        "plaque_title": None,
        "plaque_title_label": None,
        "shop_sign_style": None,
        "showcase_mood": None,
        "showcase_mood_label": None,
        "showcase_seal_line": None,
        "chat_accent": None,
    }


def cosmetics_from_row(row: Any, now: Optional[int] = None) -> Dict[str, Any]:
    if int(_row_get(row, "is_system_player", 0) or 0):
        return _empty_cosmetics()
    now = now if now is not None else int(time.time())
    monthly_expires_at = _row_get(row, "monthly_expires_at")
    shop_emblem = _row_get(row, "shop_emblem")
    showcase_tagline = _row_get(row, "showcase_tagline")
    plaque_title = _row_get(row, "plaque_title")
    shop_sign_style = _row_get(row, "shop_sign_style")
    showcase_mood = _row_get(row, "showcase_mood")
    showcase_seal_line = _row_get(row, "showcase_seal_line")
    chat_accent = _row_get(row, "chat_accent")
    is_sponsor = bool(monthly_expires_at and int(monthly_expires_at) > now)
    has_plaque = bool(shop_emblem)
    resolved_plaque_title = plaque_title if plaque_title else (DEFAULT_PLAQUE_TITLE if has_plaque else None)
    resolved_sign_style = shop_sign_style if shop_sign_style else (DEFAULT_SIGN_STYLE if has_plaque else None)
    resolved_mood = showcase_mood if showcase_mood else (DEFAULT_SHOWCASE_MOOD if has_plaque else None)
    resolved_accent = chat_accent if chat_accent else (DEFAULT_CHAT_ACCENT if has_plaque else None)
    return {
        "is_sponsor": is_sponsor,
        "sponsor_title": SPONSOR_TITLE if is_sponsor else None,
        "monthly_expires_at": int(monthly_expires_at) if monthly_expires_at else None,
        "shop_emblem": shop_emblem,
        "shop_emblem_label": EMBLEM_LABELS.get(shop_emblem) if shop_emblem else None,
        "has_plaque": has_plaque,
        "showcase_tagline": showcase_tagline or None,
        "plaque_title": resolved_plaque_title,
        "plaque_title_label": PLAQUE_TITLE_LABELS.get(resolved_plaque_title) if resolved_plaque_title else None,
        "shop_sign_style": resolved_sign_style,
        "shop_sign_style_label": SIGN_STYLE_LABELS.get(resolved_sign_style) if resolved_sign_style else None,
        "showcase_mood": resolved_mood,
        "showcase_mood_label": SHOWCASE_MOOD_LABELS.get(resolved_mood) if resolved_mood else None,
        "showcase_seal_line": showcase_seal_line or None,
        "chat_accent": resolved_accent,
        "chat_accent_label": CHAT_ACCENT_LABELS.get(resolved_accent) if resolved_accent else None,
    }


def merge_cosmetics_into_player(player: Dict[str, Any], row: Any, now: Optional[int] = None) -> Dict[str, Any]:
    merged = dict(player)
    merged.update(cosmetics_from_row(row, now))
    return merged


def attach_cosmetics(entry: Dict[str, Any], row: Any, now: Optional[int] = None) -> Dict[str, Any]:
    payload = cosmetics_from_row(row, now)
    for key in (
        "is_sponsor",
        "sponsor_title",
        "shop_emblem",
        "shop_emblem_label",
        "showcase_tagline",
        "plaque_title",
        "plaque_title_label",
        "shop_sign_style",
        "showcase_mood",
        "showcase_seal_line",
        "chat_accent",
    ):
        entry[key] = payload.get(key)
    return entry
