from typing import Any, Dict

PRODUCTS: Dict[str, Dict[str, Any]] = {
    "monthly_card": {
        "id": "monthly_card",
        "name": "掌柜月卡",
        "price_fen": 500,
        "price_label": "¥5",
        "days": 30,
        "description": "金色店招、排行榜赞助铭牌、称号「赞助掌柜」，有效期 30 天。",
    },
    "plaque_permanent": {
        "id": "plaque_permanent",
        "name": "当铺匾额（永久）",
        "price_fen": 1000,
        "price_label": "¥10",
        "description": "店名旁匾额装饰；橱窗封面自定义文案（最多 80 字）。",
    },
}

VALID_EMBLEMS = frozenset({"plaque", "seal", "lantern"})
EMBLEM_LABELS = {"plaque": "匾", "seal": "印", "lantern": "灯"}
SPONSOR_TITLE = "赞助掌柜"
MONTHLY_SECONDS = 30 * 86400
TAGLINE_MAX_LEN = 80
