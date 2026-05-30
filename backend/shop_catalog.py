from typing import Any, Dict

PRODUCTS: Dict[str, Dict[str, Any]] = {
    "monthly_card": {
        "id": "monthly_card",
        "name": "掌柜月卡",
        "price_fen": 500,
        "price_label": "¥5",
        "days": 30,
        "description": "顶栏流光店招动效、排行榜赞助铭牌、称号「赞助掌柜」，有效期 30 天。",
    },
    "plaque_permanent": {
        "id": "plaque_permanent",
        "name": "当铺匾额（永久）",
        "price_fen": 1000,
        "price_label": "¥10",
        "description": "永久称号、店招静光主题、8 种匾额样式、橱窗品牌封面（气质+落款）、谈判气泡皮肤；与月卡可叠加，月卡流光与「赞助」铭牌仍仅月卡享有。",
    },
}

VALID_EMBLEMS = frozenset({"plaque", "seal", "lantern", "bell", "ding", "jade", "scroll", "coin"})
EMBLEM_LABELS = {
    "plaque": "匾",
    "seal": "印",
    "lantern": "灯",
    "bell": "钟",
    "ding": "鼎",
    "jade": "玉",
    "scroll": "卷",
    "coin": "钱",
}

VALID_PLAQUE_TITLES = frozenset({"heritage", "veteran", "gilded"})
PLAQUE_TITLE_LABELS = {
    "heritage": "传世掌柜",
    "veteran": "名匾老铺",
    "gilded": "金字招牌",
}
DEFAULT_PLAQUE_TITLE = "heritage"

VALID_SIGN_STYLES = frozenset({"classic", "carved", "gilded"})
SIGN_STYLE_LABELS = {"classic": "经典金字", "carved": "刻匾", "gilded": "静光"}
DEFAULT_SIGN_STYLE = "classic"

VALID_SHOWCASE_MOODS = frozenset({"plain", "letter", "couplet"})
SHOWCASE_MOOD_LABELS = {"plain": "素面", "letter": "信笺", "couplet": "对联"}
DEFAULT_SHOWCASE_MOOD = "plain"

VALID_CHAT_ACCENTS = frozenset({"default", "bronze", "jade"})
CHAT_ACCENT_LABELS = {"default": "默认", "bronze": "铜色", "jade": "玉色"}
DEFAULT_CHAT_ACCENT = "default"

SPONSOR_TITLE = "赞助掌柜"
MONTHLY_SECONDS = 30 * 86400
TAGLINE_MAX_LEN = 80
SEAL_LINE_MAX_LEN = 16
